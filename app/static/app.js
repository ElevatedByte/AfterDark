'use strict';
const $ = id => document.getElementById(id);
const names = {normal_camera:'Normal Camera',pumpkin_dance:'Pumpkin Dance',skeleton_dance:'Skeleton Dance',ghost_mode:'Ghost Mode',magic_mode:'Magic Mode'};
const effects = {pumpkin_head:['◈','Pumpkin Head'],witch:['✧','Witch'],frankenstein:['▣','Frankenstein'],vampire:['♜','Vampire'],mummy:['▤','Mummy'],skeleton:['☠','Skeleton Head + Body'],bats:['⌁','Bats'],ghost:['♧','Ghost Trail / Appearance'],magic:['✦','Magic Particles'],lightning:['ϟ','Lightning']};
let state = null, socket, toastTimer, lastPeople = '', requestID = 0;
const sliderTimers = {};
const cueButtons = new Map();
const automationChoices = new Map();
let timingDraft = false, sceneryDraft = false;
const sceneryFields = ['scenery_houses','scenery_graves','scenery_pumpkins','scenery_trees'];
for (const key of sceneryFields) $(key).oninput=()=>{sceneryDraft=true;};
$('scenery_webs').onchange=e=>command({action:'settings',settings:{scenery_webs:e.target.value}});
$('scenery_enabled').onchange=e=>command({action:'settings',settings:{scenery_enabled:e.target.checked}});
$('scenery-form').onsubmit=e=>{
  e.preventDefault();
  const counts=Object.fromEntries(sceneryFields.map(key=>[key,Number($(key).value)]));
  if (command({action:'scenery_generate',settings:{...counts,scenery_webs:$('scenery_webs').value}})) sceneryDraft=false;
};
function renderScenery(s) {
  $('scenery_enabled').checked=!!s.scenery_enabled;
  $('scenery_webs').value=s.scenery_webs || 'none';
  if (!sceneryDraft) for (const key of sceneryFields) if(document.activeElement!==$(key)) $(key).value=s[key];
  $('scenery-status').textContent=(s.scenery_enabled?'Showing':'Hidden')+' · '+s.scenery_houses+' houses · '+s.scenery_graves+' graves · '+s.scenery_pumpkins+' jack-o’-lanterns · '+s.scenery_trees+' trees · Webs: '+(s.scenery_webs || 'none');
}
function renderAutomation(s) {
  for (const group of ['Visitors','Effects']) {
    for (const [key, item] of Object.entries(s.auto_catalog || {})) {
      if (item.group !== group || automationChoices.has(key)) continue;
      let fieldset=$('auto-group-'+group);
      if (!fieldset) {
        fieldset=document.createElement('fieldset');fieldset.id='auto-group-'+group;
        const legend=document.createElement('legend');legend.textContent=group;
        fieldset.append(legend);$('automation-choices').append(fieldset);
      }
      const label=document.createElement('label');label.className='automation-choice';
      const input=document.createElement('input');input.type='checkbox';input.id='auto-'+key;
      const text=document.createElement('span');text.textContent=item.label;
      label.append(input,text);fieldset.append(label);automationChoices.set(key,input);
      input.onchange=()=>command({action:'settings',settings:{random_triggers:[...automationChoices].filter(([,box])=>box.checked).map(([name])=>name)}});
    }
  }
  const selected=s.random_triggers || [];
  const triggerTargets={ghost_appearance:'ghost',spawn_bats:'bats',spell_burst:'magic'};
  const eligible=selected.filter(name=>!(s.disabled_effects || []).includes(triggerTargets[name] || name));
  for (const [name,input] of automationChoices) input.checked=selected.includes(name);
  if (!timingDraft) for (const key of ['random_min_seconds','random_max_seconds']) $(key).value=s[key];
  const timing=s.random_min_seconds===s.random_max_seconds?s.random_min_seconds:s.random_min_seconds+'–'+s.random_max_seconds;
  $('automation-summary').textContent=!eligible.length?'No allowed items selected — automatic triggers are paused.':(s.random_show?'On':'Paused')+' · Every '+timing+' seconds · '+eligible.length+' allowed and selected';
}
function renderCues(s) {
  for (const [key, cue] of Object.entries(s.cue_catalog || {})) {
    if (cueButtons.has(key)) continue;
    const button = document.createElement('button');
    button.className = 'animation-cue'; button.dataset.cue = key;
    button.setAttribute('aria-label', cue.label);
    button.setAttribute('aria-describedby', 'cue-help');
    button.title = cue.description;
    const icon = document.createElement('span'); icon.className = 'cue-icon';
    icon.textContent = cue.icon; icon.setAttribute('aria-hidden', 'true');
    const label = document.createElement('b'); label.textContent = cue.label;
    const status = document.createElement('small');
    button.append(icon, label, status);
    button.onclick = () => {
      if (command({action:'trigger', value:key})) toast('Cue fired: ' + cue.label);
    };
    $('animated-cues').append(button);
    cueButtons.set(key, {button, status, duration:cue.duration});
  }
  const playing = new Set(s.active_cues || []);
  $('cue-count').textContent = playing.size ? playing.size + ' PLAYING' : 'READY';
  for (const [key, {button, status, duration}] of cueButtons) {
    const active = playing.has(key);
    button.classList.toggle('playing', active);
    status.textContent = active ? 'Playing · click to restart' : duration + ' sec · click to play';
  }
}
const allowedChoices = new Map();
function renderAllowed(s) {
  const catalog = {...effects, ...Object.fromEntries(Object.entries(s.cue_catalog || {}).map(([key,cue])=>[key,[cue.icon,cue.label]]))};
  for (const [key,[icon,label]] of Object.entries(catalog)) {
    if (allowedChoices.has(key)) continue;
    const row=document.createElement('label');row.className='effect-row';
    const text=document.createElement('span');text.textContent=icon+' '+label;
    const input=document.createElement('input');input.className='switch';input.type='checkbox';input.id='effect-'+key;input.setAttribute('aria-label',label);
    input.onchange=()=>command({action:'settings',settings:{disabled_effects:[...allowedChoices].filter(([,box])=>!box.checked).map(([name])=>name)}});
    const group=Object.hasOwn(s.cue_catalog || {},key)?'effects-visitors':['magic','bats','lightning'].includes(key)?'effects-motion':'effects-appearances';
    row.append(text,input);$(group).append(row);allowedChoices.set(key,input);
  }
  const disabled=s.disabled_effects || [];
  for (const [name,input] of allowedChoices) input.checked=!disabled.includes(name);
  $('effect-count').textContent=([...allowedChoices.keys()].filter(name=>!disabled.includes(name)).length)+' ALLOWED';
  const targets={ghost_appearance:'ghost',spawn_bats:'bats',spell_burst:'magic'};
  document.querySelectorAll('[data-trigger], [data-cue]').forEach(button=>{
    const name=button.dataset.trigger || button.dataset.cue;
    button.disabled=disabled.includes(targets[name] || name);
  });
  for (const [name,input] of automationChoices) {
    input.disabled=disabled.includes(targets[name] || name);
    input.parentElement.title=input.disabled?'Turn this on in Allowed effects to include it in the show.':'';
  }
}
$('effects-select-all').onclick=()=>command({action:'settings',settings:{disabled_effects:[]}});
$('effects-clear').onclick=()=>command({action:'settings',settings:{disabled_effects:[...allowedChoices.keys()]}});
function toast(message) { $('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5000); }
function command(payload) {
  if (!socket || socket.readyState!==WebSocket.OPEN) {toast('Controller disconnected. Reconnecting…'); return false;}
  socket.send(JSON.stringify({...payload,request_id:String(++requestID)}));
  return true;
}
function render(s) {
  state=s;
  renderCues(s);
  renderAutomation(s);
  renderAllowed(s);
  renderScenery(s);
  const requested=s.camera_requested && s.projector_requested && s.random_show;
  const running=s.camera_running && s.projector_running;
  const stopping=!s.camera_requested && !s.projector_requested && (s.camera_running || s.projector_running);
  $('show-status').textContent=stopping?'STOPPING':requested?(s.camera_error || s.projector_error || s.runtime_error?'NEEDS ATTENTION':running?'SHOW RUNNING':'STARTING'):s.camera_requested || s.projector_requested?'MANUAL CONTROL':s.random_show?'AUTOMATION ONLY':'SHOW STOPPED';
  $('show-start').disabled=requested && !s.camera_error && !s.projector_error && !s.runtime_error;
  $('show-stop').disabled=!(s.camera_requested || s.projector_requested || s.random_show || s.camera_running || s.projector_running || s.active_cues.length);
  $('settings-save-status').textContent=s.settings_save_error || (s.settings_persistence?'Settings saved automatically · restored after restart':'Settings apply to this session');
  $('camera-status').textContent=s.demo_mode && s.camera_running?'Rehearsal':s.camera_connected?'Connected':s.camera_running?'Reconnecting':'Stopped';
  $('fps').textContent=s.fps.toFixed(1);
  $('people-count').innerHTML=`${s.tracked_people_count} <small>/ ${s.max_people}</small>`;
  $('scene-status').textContent=names[s.active_scene] || s.active_scene;
  $('preview-scene').textContent=names[s.active_scene];
  $('projector-status').textContent=s.projector_running?'Live · Monitor '+s.projector_monitor_index:s.projector_requested?'Starting…':'Offline';
  $('camera-button').textContent=s.camera_requested?'■ Stop camera':'▶ Start camera';
  $('projector-button').textContent=s.projector_requested?'■ Stop projector':'↗ Start projector';
  $('preview-badge').textContent=s.demo_mode?'REHEARSAL':s.camera_connected?'● LIVE':'STANDBY';
  $('demo-banner').hidden=!s.demo_mode;
  $('resolution').textContent=s.camera_resolution.join(' × ')+' → '+s.output_resolution.join(' × ');
  $('latency').textContent=s.frame_latency_ms+' ms';
  document.querySelectorAll('[data-scene]').forEach(b=>{const active=b.dataset.scene===s.active_scene;b.classList.toggle('active',active);b.setAttribute('aria-pressed',active);});
  for(const key of ['fullscreen','debug_skeleton','adaptive_resolution','random_show']) $(key).checked=s[key];
  for(const key of ['projector_monitor_index','max_people']) if(document.activeElement!==$(key)) $(key).value=s[key];
  for(const [key,value] of Object.entries(s.effect_settings)) {
    if(document.activeElement!==$(key) && !sliderTimers[key]) {$(key).value=value;$(key+'-value').textContent=Math.round(value*100)+'%';}
  }
  const timing=s.renderer_timings?.composition_and_control;
  $('renderer-state').textContent='Renderer: '+(s.renderer_backend || 'cpu').toUpperCase()+(timing?' · composition '+timing.median_ms+' ms median / '+timing.p95_ms+' ms p95':'');
  const errors=[s.settings_save_error,s.preview_error,s.runtime_error,s.camera_error,s.tracking_error,s.projector_error].filter(Boolean);
  if(s.resolution_reduced) errors.push('Processing reduced to 640 × 480 to improve frame rate.');
  $('errors').hidden=!errors.length;$('errors').textContent=errors.join(' · ');
  $('tracker-state').textContent='Tracking: '+s.tracking_status+(s.last_gesture?' · '+s.last_gesture:'');
  const peopleKey=JSON.stringify([s.people.map(p=>p.id),s.person_effects,s.active_scene]);
  if(peopleKey!==lastPeople && !document.activeElement?.closest('#people')) {
    lastPeople=peopleKey;$('people').replaceChildren();
    if(!s.people.length){const p=document.createElement('p');p.className='muted';p.textContent='One appearance per person. Witch and Vampire get magic hands; Mummy and Skeleton Head get a skeleton body.';$('people').append(p);}
    for(const p of s.people) {
      const row=document.createElement('div');row.className='person';
      const label=document.createElement('label');label.htmlFor='person-'+p.id;label.textContent='Person '+p.id;
      const select=document.createElement('select');select.id='person-'+p.id;
      for(const [value,label] of [['scene','Automatic appearance'],...Object.entries(effects).filter(([key])=>!['magic','bats','lightning'].includes(key)).map(([k,v])=>[k,v[1]])]) select.add(new Option(label,value));
      const assigned=s.person_effects[String(p.id)];select.value=assigned===undefined?'scene':assigned.find(name=>!['magic','bats','lightning'].includes(name)) || 'scene';
      select.onchange=()=>command({action:'person_effects',person_id:p.id,effects:select.value==='scene'?null:select.value==='none'?[]:[select.value]});
      row.append(label,select);$('people').append(row);
    }
  }
}
function connect() {
  socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  socket.onopen=()=>{$('connection').textContent='Controller connected';$('connection-dot').classList.add('online');};
  socket.onmessage=e=>{try {const data=JSON.parse(e.data);if(data.data)render(data.data);if(data.type==='error')toast(data.message);}catch{toast('Could not read controller update');}};
  socket.onclose=()=>{$('show-start').disabled=true;$('show-stop').disabled=true;$('show-status').textContent='DISCONNECTED';$('connection').textContent='Reconnecting…';$('connection-dot').classList.remove('online');setTimeout(connect,1500);};
  socket.onerror=()=>socket.close();
}
for (const key of ['random_min_seconds','random_max_seconds']) $(key).oninput=()=>{timingDraft=true;$('automation-timing-error').hidden=true;};
$('automation-timing').onsubmit=e=>{
  e.preventDefault();
  const minimum=Number($('random_min_seconds').value), maximum=Number($('random_max_seconds').value);
  if (minimum>maximum) {
    $('automation-timing-error').textContent='Minimum delay must be less than or equal to maximum delay.';
    $('automation-timing-error').hidden=false;return;
  }
  if (command({action:'settings',settings:{random_min_seconds:minimum,random_max_seconds:maximum}})) {
    timingDraft=false;$('automation-timing-error').hidden=true;
  }
};
$('automation-select-all').onclick=()=>command({action:'settings',settings:{random_triggers:Object.keys(state?.auto_catalog || {})}});
$('automation-clear').onclick=()=>command({action:'settings',settings:{random_triggers:[]}});
$('show-start').onclick=()=>command({action:'show_start'});
$('show-stop').onclick=()=>command({action:'show_stop'});
$('camera-button').onclick=()=>command({action:state?.camera_requested?'camera_stop':'camera_start'});
$('projector-button').onclick=()=>command({action:state?.projector_requested?'projector_stop':'projector_start'});
document.querySelectorAll('[data-scene]').forEach(b=>b.onclick=()=>command({action:'scene',value:b.dataset.scene}));
document.querySelectorAll('[data-trigger]').forEach(b=>b.onclick=()=>{command({action:'trigger',value:b.dataset.trigger});if(!b.dataset.trigger.startsWith('reset'))toast(b.dataset.trigger==='stop_animations'?'Animations stopped':'Cue fired: '+b.textContent.replace(/[1234]/g,'').trim());});
for(const key of ['fullscreen','debug_skeleton','adaptive_resolution','random_show']) $(key).onchange=e=>command({action:'settings',settings:{[key]:e.target.checked}});
for(const key of ['max_people','projector_monitor_index']) $(key).onchange=e=>command({action:'settings',settings:{[key]:Number(e.target.value)}});
for(const key of ['effect_intensity','ghost_trail_strength','particle_amount','tracking_smoothing']) {
  $(key).oninput=e=>{const value=Number(e.target.value);$(key+'-value').textContent=Math.round(value*100)+'%';clearTimeout(sliderTimers[key]);sliderTimers[key]=setTimeout(()=>{delete sliderTimers[key];command({action:'settings',settings:{[key]:value}});},45);};
}
document.addEventListener('keydown',e=>{if(e.repeat || ['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;const cue={1:'lightning',2:'spawn_bats',3:'ghost_appearance',4:'scream'}[e.key];if(cue)command({action:'trigger',value:cue});});
$('preview').onerror=()=>setTimeout(()=>{$('preview').src='/api/preview.mjpg?retry='+Date.now();},2000);
connect();
