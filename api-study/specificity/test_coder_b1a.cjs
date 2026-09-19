// Synthetic DOM regression checks; no study cards or codes are loaded.
const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
const script = fs.readFileSync(path.join(__dirname, 'coder.html'), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function harness(cards) {
  const elements = {}, events = {}, saved = new Map(), downloads = [];
  const el = id => elements[id] ??= {style:{}, value:'', files:[], dataset:{}, classList:{toggle(){}}, addEventListener(n,f){this[n]=f;}};
  const buttons = ['1','0','U'].map(code => ({...el('button'+code), dataset:{code}}));
  const packet = {schema_version:'au-specificity-packet-v1', packet_id:'SYNTHETIC', coder_id:'FOUNDER_ADJUDICATOR', cards};
  const document = {getElementById:el, querySelectorAll:()=>buttons, activeElement:{tagName:'BODY'}, addEventListener:(n,f)=>events[n]=f,
    createElement:()=>({click(){downloads.push(this.download);}})};
  vm.runInNewContext(script, {document, localStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v)},
    Date, JSON, Set, Array, Math, Error, Blob, URL:{createObjectURL:()=> 'synthetic', revokeObjectURL(){}}, setTimeout:fn=>fn()});
  el('packetFile').files = [{text:async()=>JSON.stringify(packet)}];
  return {el,events,saved,buttons,downloads, async open(){await el('packetFile').change();el('start').click();}};
}
(async()=>{
  const empty = harness([]); await empty.open();
  assert.match(empty.el('message').textContent, /without --adjudication/);
  assert(empty.el('download').disabled);
  assert(empty.buttons.every(b=>b.disabled));
  const cards = [0,1,2].map(i=>({card_id:'synthetic-'+i,question:'Synthetic?',passage:'Synthetic.'}));
  const h = harness(cards); await h.open();
  h.events.keydown({key:'1',repeat:false}); h.events.keydown({key:'1',repeat:true});
  assert.equal(Object.keys(JSON.parse([...h.saved.values()][0]).codes).length,1);
  h.events.keydown({key:'0',repeat:false}); h.events.keydown({key:'u',repeat:false});
  assert(!h.el('download').disabled); h.el('download').click();
  assert.equal(h.downloads[0],'FOUNDER_ADJUDICATION.json');
  console.log('PASS: empty packet, repeated key suppression, normal coding, founder download filename');
})().catch(error=>{console.error(error);process.exitCode=1;});
