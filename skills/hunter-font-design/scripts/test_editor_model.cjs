const assert = require('node:assert/strict');
const M = require('../assets/proof-tool/editor-model.js');
for (const c of [['L',500,0], ['Q',250,800,500,0], ['C',50,700,450,700,500,0]]) {
  const before = [['M',0,0], c, ['Z']], contour = M.clone(before), t = .37;
  M.split(contour, 1, t);
  for (let i = 0; i <= 100; i++) {
    const u = i / 100, actual = u <= t ? M.sample(contour,1,u/t) : M.sample(contour,2,(u-t)/(1-t));
    const expected = M.sample(before,1,u);
    assert(Math.hypot(...actual.map((v,j)=>v-expected[j])) < 1e-8, 'Splitting preserves the exact curve');
  }
  const reverse = M.reverse(before);
  assert.equal(reverse.at(-1)[0], 'Z');
  assert.deepEqual(M.end(reverse[0]), M.end(reverse.at(-2)));
  assert.deepEqual(M.reverse(M.reverse(before)), M.reverse(M.reverse(M.reverse(M.reverse(before)))));
}
const contour = [['M',0,0],['C',20,100,480,100,500,0],['C',480,-100,20,-100,0,0],['Z']];
M.move(contour,0,1,[10,20]);
assert.deepEqual(contour[0],['M',10,20]);assert.deepEqual(M.end(contour.at(-2)),[10,20]);
assert.deepEqual(contour[1].slice(1,3),[30,120]);assert.deepEqual(contour[2].slice(3,5),[30,-80]);
assert.throws(()=>M.validate({advanceWidth:600,contours:[[['M',0,0],['L',300,600]]]}));
assert.throws(()=>M.validate({advanceWidth:600,contours:[[['M',NaN,0],['L',300,600],['Z']]]}));
assert.throws(()=>M.validate({advanceWidth:600,contours:[[['M',0,0],['toString'],['Z']]]}));
console.log('PASS: curve splitting, reversing, closed-node movement and validation');
