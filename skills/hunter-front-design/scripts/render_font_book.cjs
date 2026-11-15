// Render a generated book; fonts are served locally, hashed, and checked through Chromium.
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const crypto=require('node:crypto');
const {createRequire}=require('node:module');
const args=process.argv.slice(2);
if(!args.length||args.includes('--help')){console.log('node render_font_book.cjs <book-dir> [--node-root <directory containing node_modules>]');process.exit(args.length?0:2);}
const root=path.resolve(args[0]),i=args.indexOf('--node-root');
const req=i>=0?createRequire(path.join(path.resolve(args[i+1]),'noop.js')):require;
const {chromium}=req('playwright');
const info=JSON.parse(fs.readFileSync(path.join(root,'book-info.json'),'utf8'));
if(fs.existsSync(path.join(root,'fontbook.pdf')))throw Error('Use a fresh generated book; existing PDF evidence is not overwritten.');
const mime={'.html':'text/html;charset=utf-8','.ttf':'font/ttf','.otf':'font/otf','.woff':'font/woff','.woff2':'font/woff2'};
const server=http.createServer((request,response)=>{
  try{
    const name=decodeURIComponent(new URL(request.url,'http://localhost').pathname);
    const file=path.resolve(root,'.'+name);
    if(!file.startsWith(root+path.sep)||!fs.statSync(file).isFile()){response.writeHead(404);return response.end();}
    response.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');
    response.end(fs.readFileSync(file));
  }catch{response.writeHead(404);response.end();}
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    try{browser=await chromium.launch({channel:'chrome',headless:true});}
    catch{browser=await chromium.launch({headless:true});}
    const context=await browser.newContext({viewport:{width:1600,height:1000},deviceScaleFactor:1});
    const page=await context.newPage();
    const hashes=new Map(),pending=[];
    page.on('response',response=>{
      const relative=new URL(response.url()).pathname.slice(1);
      if(relative.startsWith('fonts/'))pending.push(response.body().then(bytes=>hashes.set(relative,crypto.createHash('sha256').update(bytes).digest('hex'))));
    });
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
    await page.evaluate(async()=>{await Promise.all([...document.fonts].map(font=>font.load()));await document.fonts.ready;});
    await Promise.all(pending);
    for(const font of info.fonts)if(hashes.get(font.book_file)!==font.sha256)throw Error('Loaded font hash differs: '+font.book_file);
    const fitted=await page.evaluate(()=>{
      const changed=[];
      for(const el of document.querySelectorAll('[data-fit]')){
        const original=el.textContent;
        if(el.dataset.fit==='clip-text'){
          while(el.scrollWidth>el.clientWidth+1&&el.textContent.length)el.textContent=el.textContent.slice(0,-1);
          if(original!==el.textContent)changed.push({mode:'shortened',original,shown:el.textContent});
        }else{
          let size=parseFloat(getComputedStyle(el).fontSize);
          while(el.scrollWidth>el.clientWidth+1&&size>12){size-=1;el.style.fontSize=size+'px';}
          changed.push({mode:'font-size',px:size,text:el.textContent});
        }
      }
      return changed;
    });
    const cdp=await context.newCDPSession(page);
    await cdp.send('DOM.enable');await cdp.send('CSS.enable');
    const {root:dom}=await cdp.send('DOM.getDocument',{depth:-1});
    const {nodeIds}=await cdp.send('DOM.querySelectorAll',{nodeId:dom.nodeId,selector:'[data-font]'});
    const fallbacks=[];
    for(const nodeId of nodeIds){
      const {fonts}=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
      for(const font of fonts)if(!font.isCustomFont)fallbacks.push({font:font.familyName,glyphs:font.glyphCount,nodeId});
    }
    const overflow=await page.evaluate(()=>{
      const errors=[];
      for(const section of document.querySelectorAll('.page')){
        const r=section.getBoundingClientRect();
        for(const el of section.querySelectorAll('main *')){
          const b=el.getBoundingClientRect();
          if(b.width&&(b.left<r.left+40||b.right>r.right-40||b.bottom>r.bottom-28||el.scrollWidth>el.clientWidth+2&&el.dataset.fit))errors.push({page:section.id,element:el.tagName,class:el.className});
        }
      }
      return errors;
    });
    fs.mkdirSync(path.join(root,'pages'),{recursive:true});
    const sections=await page.locator('.page').all();
    for(let index=0;index<sections.length;index++)await sections[index].screenshot({path:path.join(root,'pages',String(index+1).padStart(3,'0')+'.png')});
    const result={status:fallbacks.length||overflow.length||info.missing_codepoints?'fail':'pass',fonts:info.fonts.map(font=>({sha256:font.sha256,file:font.book_file})),pages:sections.length,fallbacks,overflow,missing_codepoints:info.missing_codepoints,fitting:fitted};
    fs.writeFileSync(path.join(root,'render-report.json'),JSON.stringify(result,null,2)+'\n');
    if(result.status!=='pass')throw Error(`Book failed: ${fallbacks.length} fallback fonts, ${overflow.length} overflows, ${info.missing_codepoints} missing characters.`);
    await page.emulateMedia({media:'print'});
    await page.pdf({path:path.join(root,'fontbook.pdf'),width:'1600px',height:'1000px',printBackground:true,preferCSSPageSize:true});
    console.log(JSON.stringify({status:'pass',pages:sections.length,pdf:path.join(root,'fontbook.pdf')}));
  }finally{
    if(browser)await browser.close();
    await new Promise(resolve=>server.close(resolve));
  }
})().catch(error=>{console.error(error.message);process.exitCode=1;});
