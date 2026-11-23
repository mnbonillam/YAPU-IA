'use strict';
let monitor=null, selectedParcel=0;
const zoneCenters={Viacha:[-16.65,-68.30],Achacachi:[-16.05,-68.68],Patacamaya:[-17.24,-67.92],Tarata:[-17.61,-66.02],"Yamparáez":[-19.18,-65.12],"La Paz":[-16.536172,-68.06435],"Palos Blancos":[-15.564881,-67.319786],Tiraque:[-17.47645,-65.652847]};
function opButton(key,label,value='',cls='ghost'){
 return `<button type="button" data-op="${key}" data-value="${h(value)}" class="${cls}">${h(label)}</button>`;
}
function stopMonitor(){
 if(!monitor)return;
 clearInterval(monitor.timer);monitor.abort.abort();monitor.map.remove();monitor=null;
}
function startMonitor(){
 $('#app').innerHTML=`<div class="ops-title"><div><div class="eyebrow">NEXTECH · Operaciones agrícolas</div><h1>Centro de monitoreo</h1><div class="op-sync"><span id="opdot" class="op-dot off"></span><span id="opsync" class="op-status">Conectando al servidor…</span></div></div>${opButton('new','+ Registrar parcela','','op-cta')}</div>
 <div id="opstats" class="op-stats"></div><div class="op-split"><section class="op-block"><div class="heading"><h2>Mapa operativo</h2><small id="scope"></small></div><div id="opmap" class="op-map" aria-label="Mapa interactivo de parcelas"></div><small id="mapnote">Selecciona un marcador para consultar la parcela.</small></section>
 <section class="op-block"><div class="heading"><h2>Clima por parcela</h2><small>Open-Meteo</small></div><label>Ubicación<select id="opselect"></select></label><div id="opweather"></div><div class="op-tool op-actions">${opButton('update','Actualizar clima','','op-cta')}${opButton('edit','Editar parcela')}</div></section></div>
 <section class="op-block"><div class="heading"><div><span class="eyebrow">Evidencia y acuse de recibo</span><h2>Alertas de campo</h2></div><select id="opfilter" aria-label="Filtrar alertas" style="max-width:180px"><option>Abiertas</option><option>Acusadas</option><option>Todas</option></select></div><div id="opalerts" class="op-alerts"></div></section>
 <section class="op-block"><div class="heading"><h2>Mensajes de la parcela</h2><small id="opchannel"></small></div><div id="opmsgs" class="op-list"></div><form id="opmsg" data-ops class="op-tool"><label style="flex:1">Mensaje al equipo o al productor<input name="text" maxlength="1000" required placeholder="Escribe un mensaje en el panel…"></label><button class="op-cta">Enviar al panel</button><button class="ghost" value="ask">Consultar al asistente</button><button id="sendwa" class="ghost" name="channel" value="whatsapp">Responder por WhatsApp</button></form></section>`;
 const map=L.map('opmap',{scrollWheelZoom:false}).setView(zoneCenters.Viacha,9);
 const m={map,abort:new AbortController(),markers:L.layerGroup().addTo(map),data:null,sig:'',ref:null,refTime:0,loading:false};
 monitor=m;
 const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
 tiles.on('tileerror',()=>{if(monitor===m)$('#mapnote').textContent='Cartografía sin conexión. El selector conserva las coordenadas de las parcelas.'});
 $('#opselect').onchange=e=>selectParcel(Number(e.target.value),true);$('#opfilter').onchange=()=>paintBoard(m);
 syncBoard(m).then(()=>listenBoard(m));m.timer=setInterval(()=>{if(!document.hidden&&!m.listening)syncBoard(m)},4000);
}
async function listenBoard(m){
 while(m===monitor){
  try{
   m.listening=true;
   const response=await fetch('/api/ops/wait?seen='+(m.data?.version??-1),{headers:{'X-Yapu-Admin':adminKey},signal:m.abort.signal});
   if(!response.ok)throw Error('Conexión interrumpida');
   await response.json();if(m!==monitor)return;await syncBoard(m);
  }catch(e){
   if(m!==monitor)return;m.listening=false;await new Promise(done=>setTimeout(done,4000));
  }
 }
}
async function reference(m,force=false){
 if(m.refLoading||(!force&&Date.now()-m.refTime<600000))return;
 m.refLoading=true;m.refTime=Date.now();
 try{m.ref=await api('reference'+(force?'?refresh=1':''));m.refError=''}catch(e){m.refError=e.message}
 finally{m.refLoading=false;if(m===monitor&&m.data)paintBoard(m)}
}
async function syncBoard(m){
 if(m!==monitor||m.loading)return;
 m.loading=true;
 try{
  const d=await api('ops');if(m!==monitor)return;m.data=d;
  if(!d.parcels.some(p=>p.number===selectedParcel))selectedParcel=d.parcels[0]?.number||0;
  paintBoard(m);$('#opdot').className='op-dot';$('#opsync').textContent='Panel conectado · '+new Date().toLocaleTimeString('es-BO',{timeZone:'America/La_Paz'})+' (Bolivia)';
  if(!d.parcels.length)reference(m);
 }catch(e){if(m===monitor){$('#opdot').className='op-dot off';$('#opsync').textContent='Sin sincronizar · '+e.message}}
 finally{m.loading=false}
}
function selectParcel(n,center){
 const m=monitor,p=m?.data.parcels.find(x=>x.number===n);if(!p)return;
 selectedParcel=n;paintBoard(m);if(center)m.map.setView([p.lat,p.lon],Math.max(11,m.map.getZoom()));
}
function paintBoard(m){
 if(m!==monitor||!m.data)return;
 const d=m.data, p=d.parcels.find(x=>x.number===selectedParcel);
 const num=d.alerts.filter(x=>!x.ack).length;
 $('#opstats').innerHTML=[['Parcelas registradas',d.parcels.length],['Clima vigente',d.parcels.filter(x=>x.weather&&!x.error).length],['Alertas abiertas',num],['Con acuse',d.alerts.length-num]].map(([t,v])=>`<div class="op-stat"><small>${t}</small><b>${v}</b></div>`).join('');
 $('#scope').textContent=d.team?'Todas las parcelas · Equipo':'Mis parcelas';
 const choices=d.parcels.map(x=>`<option value="${x.number}">${h(x.name)} · #${x.number}</option>`).join('')||'<option value="0">Viacha · referencia municipal</option>';
 const sel=$('#opselect');if(sel.innerHTML!==choices)sel.innerHTML=choices;sel.value=selectedParcel;
 const sig=JSON.stringify(d.parcels.map(x=>[x.number,x.name,x.lat,x.lon,x.error,!!x.weather,d.alerts.some(a=>a.number===x.number&&!a.ack)]));
 if(sig!==m.sig){
  const first=!m.sig;m.sig=sig;m.markers.clearLayers();const bounds=[];
  for(const x of d.parcels){const alert=d.alerts.some(a=>a.number===x.number&&!a.ack);
   const pt=[x.lat,x.lon];bounds.push(pt);L.circleMarker(pt,{radius:9,color:'#fff7de',weight:2,fillOpacity:1,fillColor:alert?'#b24e37':x.weather&&!x.error?'#347454':'#867b62'}).addTo(m.markers).bindTooltip(h(x.name)).on('click',()=>selectParcel(x.number,false));}
  if(first&&bounds.length)m.map.fitBounds(bounds,{maxZoom:11,padding:[28,28]});
 }
 $('#app [data-op="edit"]').hidden=!p;
 const w=p?p.weather:m.ref,warning=p?p.error:m.refError,loc=p?`${p.located?'Coordenadas registradas':'Referencia municipal'} · ${p.lat}, ${p.lon}`:'Referencia municipal de Viacha · −16.65, −68.30';
 $('#opweather').innerHTML=`<p class="op-kicker">${h(loc)}</p>${warning?`<p class="note">${h(warning)}${w?' · Último registro disponible.':''}</p>`:''}`+(w?`<strong class="op-deg">${h(w.current.temperature_2m)}°</strong><small>Temperatura del modelo · ${h(w.valid.replace('T',' '))}</small><div class="op-data">${[['Humedad',w.current.relative_humidity_2m+' %'],['Viento',w.current.wind_speed_10m+' km/h'],['Precipitación',w.current.precipitation+' mm']].map(([k,v])=>`<div><small>${k}</small><b>${v}</b></div>`).join('')}</div><div class="eyebrow">Pronóstico de tres días</div><div class="op-data">${w.days.slice(0,3).map(x=>`<div><small>${h(dlabel(x.date))}</small><b>${x.high}° / ${x.low}°</b><small>${x.prob}% lluvia</small></div>`).join('')}</div><small>Consulta ${h(w.stamp.replace('T',' '))}</small>`:'<p class="op-empty">Esperando datos meteorológicos.</p>');
 const filter=$('#opfilter').value;
 const alerts=d.alerts.filter(a=>filter==='Todas'||(filter==='Abiertas'?!a.ack:!!a.ack));
 $('#opalerts').innerHTML=alerts.map(a=>`<article class="op-alert ${a.level==='Alto'?'alto':''}"><div class="heading"><h3>${h(a.kind)}</h3><span class="pill">${a.level}</span></div><b>${h(a.name)}</b><small> · ${a.day}</small><p>${h(a.evidence)}. ${h(a.action)}</p><small>${h(a.source)} · ${h(a.stamp)}${d.parcels.find(x=>x.number===a.number)?.error?' · Pendiente de actualización':''}</small><div class="op-actions">${a.ack?`<small>Acusada · ${h(a.ack)}</small>`:opButton('ack','Acusar recibo',a.id)}</div></article>`).join('')||'<p class="op-empty">Sin avisos en este filtro. Las alertas se crean cuando un pronóstico supera un umbral.</p>';
 $('#opchannel').textContent=d.whatsapp?(d.template?'WhatsApp configurado · plantilla definida':'WhatsApp configurado · falta plantilla'):'WhatsApp pendiente de configurar';
 const messages=d.messages.filter(x=>x.number===selectedParcel);
 const status={accepted:'Aceptado por Meta',sent:'Enviado',delivered:'Entregado',read:'Leído',failed:'Fallido'};
 $('#opmsgs').innerHTML=messages.map(x=>`<div class="op-msg"><b>${h(x.direction)}</b><small> · ${h(x.channel)} · ${h(x.stamp)}</small><p>${h(x.body)}</p><small>${h(status[x.status]||'')}${x.detail?' · '+h(x.detail):''}</small></div>`).join('')||'<p class="op-empty">Todavía no hay mensajes para esta parcela.</p>';
 $('#opmsg').hidden=!p;$('#sendwa').hidden=!(p?.wa&&d.team&&d.whatsapp&&Date.now()/1000-p.last_inbound<86400);
}
function parcelEditor(p){
 const loc=p?[p.lat,p.lon]:zoneCenters.Viacha;
 modal(`<h2>${p?'Editar':'Registrar'} parcela</h2><form id="opparcel" data-ops class="form"><input type="hidden" name="number" value="${p?.number||''}"><label>Nombre<input name="name" required maxlength="60" value="${h(p?.name||'')}" placeholder="Nombre de tu parcela"></label>${field('zone','Municipio',s.zones,p?.zone||'Viacha')}<div class="two">${field('crop','Cultivo',s.crops,p?.crop)}${field('stage','Etapa',s.stages,p?.stage)}</div><div class="two"><label>Latitud<input name="lat" type="number" min="-90" max="90" step="any" required value="${loc[0]}"></label><label>Longitud<input name="lon" type="number" min="-180" max="180" step="any" required value="${loc[1]}"></label></div><small>Las coordenadas iniciales son del centro municipal. Reemplázalas por las de tu terreno.</small>${opButton('gps','Usar mi ubicación')}<label class="check"><input name="consent" type="checkbox" required>Autorizo guardar la ubicación y consultar el clima de esta parcela.</label><button>Guardar y consultar clima</button><div class="error"></div></form>`);
 $('#opparcel [name=zone]').onchange=e=>{const [lat,lon]=zoneCenters[e.target.value];const f=$('#opparcel');f.elements.lat.value=lat;f.elements.lon.value=lon};
}
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-op]');if(!b)return;const m=monitor;const k=b.dataset.op;b.disabled=true;
 try{
 const d=m?.data;if(!d)throw Error('Esperando conexión al servidor.');
 if(k==='new'||k==='edit')parcelEditor(k==='edit'?d.parcels.find(x=>x.number===selectedParcel):null);
 if(k==='gps'){if(!navigator.geolocation)throw Error('GPS no disponible. Ingresa las coordenadas.');const pos=await new Promise((ok,bad)=>navigator.geolocation.getCurrentPosition(ok,bad,{timeout:10000}));const f=$('#opparcel');f.elements.lat.value=pos.coords.latitude.toFixed(6);f.elements.lon.value=pos.coords.longitude.toFixed(6)}
 if(k==='update'){if(selectedParcel)await api('ops/refresh',{number:selectedParcel});else await reference(m,true);await syncBoard(m)}
 if(k==='ack'){const a=d.alerts.find(x=>x.id===Number(b.dataset.value));await api('ops/ack',{number:a.number,alert:a.id});await syncBoard(m)}
 }catch(err){notify(err.message);if(m)await syncBoard(m)}finally{b.disabled=false}
});
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.hasAttribute('data-ops'))return;e.preventDefault();const m=monitor;const b=f.querySelector('button:not([type=button])');if(b.disabled)return;b.disabled=true;
 try{
 if(f.id==='opmsg'){await api(e.submitter?.value==='whatsapp'?'ops/whatsapp':e.submitter?.value==='ask'?'ops/ask':'ops/message',{number:selectedParcel,text:f.elements.text.value});f.reset()}
 if(f.id==='opparcel'){
  const val=formData(f);val.consent=f.elements.consent.checked;
  const r=await api('ops/parcel',val);selectedParcel=r.number;closeModal();await syncBoard(m);selectParcel(r.number,true);notify('Parcela guardada. Consultando Open-Meteo…');
  await api('ops/refresh',{number:r.number});
 }
 await syncBoard(m);
 }catch(err){const el=f.querySelector('.error');if(el&&el.isConnected)el.textContent=err.message;notify(err.message);await syncBoard(m)}finally{b.disabled=false}
});
