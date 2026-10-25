'use strict';
const $ = id => document.getElementById(id);
const names = {normal_camera:'Normal Camera',pumpkin_dance:'Pumpkin Dance',skeleton_dance:'Skeleton Dance',ghost_mode:'Ghost Mode',magic_mode:'Magic Mode'};
const effects = {pumpkin_head:['◈','Pumpkin Head'],witch:['✧','Witch'],frankenstein:['▣','Frankenstein'],vampire:['♜','Vampire'],mummy:['▤','Mummy'],skeleton:['☠','Skeleton'],bats:['⌁','Bats'],ghost:['♧','Ghost Trail'],magic:['✦','Magic Particles'],lightning:['ϟ','Lightning']};
let state = null, socket, toastTimer, lastPeople = '', requestID = 0;
const sliderTimers = {};
const cueButtons = new Map();
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
for (const [key,[icon,label]] of Object.entries(effects)) {
  const row=document.createElement('label');row.className='effect-row';
  row.innerHTML=`<span><span class="effect-icon">${icon}</span>${label}</span><input class="switch" type="checkbox" id="effect-${key}" aria-label="${label}">`;
  $('effects').append(row);
  row.querySelector('input').addEventListener('change',e=>command({action:e.target.checked?'effect_enable':'effect_disable',value:key}));
}
function toast(message) { $('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5000); }
function command(payload) {
  if (!socket || socket.readyState!==WebSocket.OPEN) {toast('Controller disconnected. Reconnecting…'); return false;}
  socket.send(JSON.stringify({...payload,request_id:String(++requestID)}));
  return true;
}
function render(s) {
  state=s;
  renderCues(s);
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
  $('effect-count').textContent=s.active_effects.length+' ACTIVE';
  for(const key of Object.keys(effects)) $('effect-'+key).checked=s.active_effects.includes(key);
  document.querySelectorAll('[data-scene]').forEach(b=>{const active=b.dataset.scene===s.active_scene;b.classList.toggle('active',active);b.setAttribute('aria-pressed',active);});
  for(const key of ['fullscreen','debug_skeleton','adaptive_resolution','random_show']) $(key).checked=s[key];
  for(const key of ['projector_monitor_index','max_people']) if(document.activeElement!==$(key)) $(key).value=s[key];
  for(const [key,value] of Object.entries(s.effect_settings)) {
    if(document.activeElement!==$(key) && !sliderTimers[key]) {$(key).value=value;$(key+'-value').textContent=Math.round(value*100)+'%';}
  }
  const timing=s.renderer_timings?.composition_and_control;
  $('renderer-state').textContent='Renderer: '+(s.renderer_backend || 'cpu').toUpperCase()+(timing?' · composition '+timing.median_ms+' ms median / '+timing.p95_ms+' ms p95':'');
  const errors=[s.preview_error,s.runtime_error,s.camera_error,s.tracking_error,s.projector_error].filter(Boolean);
  if(s.resolution_reduced) errors.push('Processing reduced to 640 × 480 to improve frame rate.');
  $('errors').hidden=!errors.length;$('errors').textContent=errors.join(' · ');
  $('tracker-state').textContent='Tracking: '+s.tracking_status+(s.last_gesture?' · '+s.last_gesture:'');
  const peopleKey=JSON.stringify([s.people.map(p=>p.id),s.person_effects,s.active_scene]);
  if(peopleKey!==lastPeople && !document.activeElement?.closest('#people')) {
    lastPeople=peopleKey;$('people').replaceChildren();
    if(!s.people.length){const p=document.createElement('p');p.className='muted';p.textContent='New people start with random effects in Normal Camera, or the selected mode. You can change each person afterward.';$('people').append(p);}
    for(const p of s.people) {
      const row=document.createElement('div');row.className='person';
      const label=document.createElement('label');label.htmlFor='person-'+p.id;label.textContent='Person '+p.id;
      const select=document.createElement('select');select.id='person-'+p.id;
      for(const [value,label] of [['scene','Follow scene'],['none','No effects'],...Object.entries(effects).map(([k,v])=>[k,v[1]])]) select.add(new Option(label,value));
      const assigned=s.person_effects[String(p.id)];select.value=assigned===undefined?'scene':assigned.length?assigned[0]:'none';
      select.onchange=()=>command({action:'person_effects',person_id:p.id,effects:select.value==='scene'?null:select.value==='none'?[]:[select.value]});
      row.append(label,select);$('people').append(row);
    }
  }
}
function connect() {
  socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  socket.onopen=()=>{$('connection').textContent='Controller connected';$('connection-dot').classList.add('online');};
  socket.onmessage=e=>{try {const data=JSON.parse(e.data);if(data.data)render(data.data);if(data.type==='error')toast(data.message);}catch{toast('Could not read controller update');}};
  socket.onclose=()=>{$('connection').textContent='Reconnecting…';$('connection-dot').classList.remove('online');setTimeout(connect,1500);};
  socket.onerror=()=>socket.close();
}
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
