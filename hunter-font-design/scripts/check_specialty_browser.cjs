// Verify actual HTTP font bytes, custom-font rendering, color pixels, axes, vertical and MathML.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {createHash}=require('node:crypto');
const hash=b=>createHash('sha256').update(b).digest('hex');

(async()=>{
  const root=path.resolve(process.argv[2]||'');
  assert(fs.existsSync(path.join(root,'gallery/manifest.json')),'Usage: node check_specialty_browser.cjs /absolute/lab-report');
  assert(!fs.existsSync(path.join(root,'browser.json')),'Use a fresh browser report directory.');
  const types={'.woff2':'font/woff2','.ttf':'font/ttf','.otf':'font/otf','.html':'text/html; charset=utf-8','.json':'application/json','.svg':'image/svg+xml'};
  const server=http.createServer((req,res)=>{
    const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
    if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404).end();return;}
    const bytes=fs.readFileSync(file),etag='"'+hash(bytes)+'"';
    res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('ETag',etag);
    res.setHeader('Cache-Control','public, max-age=0, must-revalidate');
    res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');
    if(req.headers['if-none-match']===etag){res.writeHead(304).end();return;}
    res.end(bytes);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin='http://127.0.0.1:'+server.address().port;
  let browser;
  try{
    browser=await chromium.launch({channel:'chrome',headless:true});
    const page=await browser.newPage({viewport:{width:1240,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>assert(new URL(r.url()).origin===origin,'Unexpected external resource.'));
    await page.goto(origin+'/gallery/index.html');
    await page.evaluate(()=>document.fonts.ready);
    const manifest=JSON.parse(fs.readFileSync(path.join(root,'gallery/manifest.json')));
    const loaded=[];
    for(const row of manifest){
      const response=await page.request.get(origin+'/gallery/'+row.url);
      assert(response.ok());assert.equal(hash(await response.body()),row.sha256);
      assert.equal(response.headers()['content-type'],types[path.extname(row.url)]);
      const cache=await page.request.get(origin+'/gallery/'+row.url,{headers:{'If-None-Match':response.headers().etag}});
      assert.equal(cache.status(),304);
      loaded.push({id:row.id,sha256:row.sha256,mime:response.headers()['content-type'],etag_304:true});
    }
    const cdp=await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');await cdp.send('CSS.enable');
    const {root:dom}=await cdp.send('DOM.getDocument');
    const rendered=[];
    for(const row of manifest){
      const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:dom.nodeId,selector:'#'+row.id});
      const fonts=(await cdp.send('CSS.getPlatformFontsForNode',{nodeId})).fonts;
      assert(fonts.some(f=>f.isCustomFont&&f.glyphCount>0),'No custom glyphs rendered for '+row.id);
      assert(!fonts.some(f=>!f.isCustomFont&&f.glyphCount>0),'Fallback rendered for '+row.id);
      rendered.push({id:row.id,fonts});
    }
    const mathNodes=await cdp.send('DOM.querySelectorAll',{nodeId:dom.nodeId,selector:'#math mi,#math mo,#math mn'});
    const mathFonts=[];
    for(const nodeId of mathNodes.nodeIds){
      const fonts=(await cdp.send('CSS.getPlatformFontsForNode',{nodeId})).fonts;
      assert(fonts.some(f=>f.isCustomFont&&f.glyphCount>0),'MathML token did not use the real math font.');
      assert(!fonts.some(f=>!f.isCustomFont&&f.glyphCount>0),'MathML token fell back to a system font.');
      mathFonts.push(fonts);
    }
    const canvasResults=await page.evaluate(()=>{
      function raster(id,size,weight){
        const canvas=document.createElement('canvas');canvas.width=900;canvas.height=180;
        const c=canvas.getContext('2d',{willReadFrequently:true});
        c.font=`${weight||400} ${size}px LabFont-${id}`;c.fillStyle='black';c.fillText(document.getElementById(id).textContent,6,130);
        const data=c.getImageData(0,0,900,180).data;let colored=0,ink=0;
        for(let i=0;i<data.length;i+=4)if(data[i+3]>80){ink++;if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>35)colored++;}
        return {ink,colored,png:canvas.toDataURL()};
      }
      const colors=Object.fromEntries(['colr0','colr1','emoji','bitmap'].map(id=>[id,raster(id,id==='bitmap'?32:96)]));
      const light=raster('variable',96,200),heavy=raster('variable',96,900);
      const vertical=document.getElementById('vertical'),math=document.getElementById('math');
      return {colors,variable:{different:light.png!==heavy.png,lightInk:light.ink,heavyInk:heavy.ink},
              vertical:{mode:getComputedStyle(vertical).writingMode,box:vertical.getBoundingClientRect().toJSON()},
              math:{box:math.getBoundingClientRect().toJSON(),family:getComputedStyle(math).fontFamily}};
    });
    for(const [id,result] of Object.entries(canvasResults.colors)){
      assert(result.ink>10&&result.colored>10,'No real color pixels for '+id);
      fs.writeFileSync(path.join(root,id+'-canvas.png'),Buffer.from(result.png.split(',')[1],'base64'));delete result.png;
    }
    assert(canvasResults.variable.different&&canvasResults.variable.heavyInk>canvasResults.variable.lightInk,'Axis does not alter actual pixels.');
    assert.equal(canvasResults.vertical.mode,'vertical-rl');assert(canvasResults.vertical.box.height>canvasResults.vertical.box.width);
    assert(canvasResults.math.box.height>80,'Math fraction/root/stretch layout collapsed.');
    await page.screenshot({path:path.join(root,'specialty-gallery.png'),fullPage:true});
    await page.pdf({path:path.join(root,'specialty-gallery.pdf'),format:'A4',printBackground:true});
    await page.reload();await page.evaluate(()=>document.fonts.ready);assert.equal(errors.length,0,errors.join('\n'));
    fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify({status:'pass',browser:await browser.version(),loaded,rendered,mathFonts,canvasResults,
      scope:'Local HTTP Chrome only. Production CORS/cache settings, other engines, device and language approval require their own checks.'},null,2));
    console.log(JSON.stringify({status:'pass',fonts:loaded.length,output:root}));
  }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
