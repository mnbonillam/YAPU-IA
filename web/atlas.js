'use strict';
const $=q=>document.querySelector(q), esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nav={'Resumen':'◈','Productores':'♧','Parcelas':'▧','Meteorología':'☼','Riesgos':'△','Laboratorio':'⚗','Alertas':'◉'};
let data,tab=location.hash==='#laboratorio'?'Laboratorio':'Resumen',selected=0,detail=null,map,detailRequest=0,search='',status='Todos',attempt=null,busy=false,toastTimer;
const key=p=>p.number, current=()=>data.parcels.find(p=>p.number===selected);
const btn=(a,t,v='',css='')=>`<button type="button" class="${css}" data-a="${a}" data-v="${esc(v)}">${esc(t)}</button>`;
const badge=(v)=>`<span class="pill ${v==='Alto'?'high':v==='Medio'?'med':v==='Bajo'?'low':''}">${esc(v)}</span>`;
const title=(head,sub,action='')=>`<div class="title"><div><h1>${head}</h1><p>${sub}</p></div>${action}</div>`;
const metric=(label,value)=>`<div class="metric"><small>${label}</small><b>${esc(value)}</b></div>`;
const card=(head,body,extra='')=>`<section class="card"><div class="line"><h2>${head}</h2>${extra}</div>${body}</section>`;
const table=(cols,body)=>`<div class="scroll"><table><thead><tr>${cols.map(x=>'<th>'+x+'</th>').join('')}</tr></thead><tbody>${body||`<tr><td colspan="${cols.length}">Sin registros para este filtro.</td></tr>`}</tbody></table></div>`;
const opts=(a,v)=>a.map(x=>`<option ${v===x?'selected':''}>${esc(x)}</option>`).join('');
const select=(k,label,a,v)=>`<label>${label}<select name="${k}">${opts(a,v)}</select></label>`;
const input=(k,label,value='',type='text',attrs='')=>`<label>${label}<input name="${k}" type="${type}" value="${esc(value)}" ${attrs}></label>`;
const stamp=t=>(t||'').replace('T',' ').slice(0,16), f=(v,d=1)=>v==null?'—':Number(v).toLocaleString('es-BO',{maximumFractionDigits:d});
const producer=id=>data.producers.find(x=>x.id===id);
const alertLevel=kind=>['Aire seco','Déficit de lluvia','Cambio brusco'].includes(kind)?'Medio':'Alto';
const parcelLevel=n=>{const a=data.alerts.filter(x=>x.number===n);return a.some(x=>x.level==='Alto')?'Alto':a.length?'Medio':data.parcels.find(x=>x.number===n)?.weather&&!data.parcels.find(x=>x.number===n)?.error?'Bajo':'Sin dato vigente'};
function toast(t){$('#toast').textContent=t;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').textContent='',6000)}
async function api(path,body){const r=await fetch('/api/'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw Error(j.error||'Error de conexión');return j}
function choose(){return `<label>Parcela seleccionada<select id="choice">${data.parcels.map(p=>`<option value="${p.number}" ${selected===p.number?'selected':''}>${esc(p.name)} · ${esc(p.zone)}</option>`).join('')}</select></label>`}
function displayDialog(html){$('#modal').innerHTML=html;if(!$('dialog').open)$('dialog').showModal()}
function lineplot(vals){
 const v=vals.map(x=>x.temp);if(v.length<2)return '<p>Sin serie disponible.</p>';
 const low=Math.floor(Math.min(...v)),hi=Math.ceil(Math.max(...v)),y=x=>112-(x-low)*85/(hi-low||1),X=i=>38+i*538/(v.length-1);
 const points=v.map((t,i)=>X(i).toFixed(1)+','+y(t).toFixed(1)).join(' ');
 return `<svg viewBox="0 0 600 140" class="plot" role="img" aria-label="Temperatura de ${esc(stamp(vals[0].hora))} a ${esc(stamp(vals.at(-1).hora))}, entre ${low} y ${hi} grados"><path d="M38 26H576 M38 70H576 M38 112H576" stroke="#cfdac9" stroke-dasharray="4 4"/><polygon points="38,112 ${points} 576,112" fill="#dce8d6"/><polyline points="${points}" stroke="#376e53" stroke-width="2.4" fill="none"/><g fill="#536356" font-size="12"><text x="5" y="30">${hi}°</text><text x="5" y="115">${low}°</text><text x="38" y="134">${esc(vals[0].hora.slice(5,10))}</text><text x="537" y="134">${esc(vals.at(-1).hora.slice(5,10))}</text></g></svg>`;
}
function climateCard(){
 const p=current(),w=p?.weather;if(!w)return card('Clima de la parcela','<p>Actualiza la ubicación para obtener la primera consulta.</p>');
 return card('Clima de la parcela',`<small>${esc(p.zone)} · ${esc(p.crop)} · ${esc(p.stage)}</small><div class="num">${f(w.current.temperature_2m)} °C</div><p>Humedad <b>${f(w.current.relative_humidity_2m)} %</b> · Viento <b>${f(w.current.wind_speed_10m)} km/h</b></p><p>Dirección <b>${f(w.current.wind_direction_10m)}°</b> · Precipitación <b>${f(w.current.precipitation)} mm</b></p><small>${esc(w.source)} · Dato ${esc(stamp(w.valid))} (Bolivia)</small>${p.error?`<div class="notice">${esc(p.error)}. Se muestra la última lectura guardada.</div>`:''}<div class="tools">${btn('refresh','Actualizar clima',p.number)}</div>`,badge(p.error?'Última captura':'Modelo meteorológico'));
}
function dashboard(){
 const p=current(),h=detail?.history?.slice().reverse().filter(x=>x.temp!=null)||[],last=data.audit.slice(0,4);
 return `<section class="hero title"><div><span class="kicker">YAPU · ATLAS AGROCLIMÁTICO</span><h1>Panorama del campo</h1><p>Parcelas, condiciones del tiempo y avisos en Bolivia.</p></div>${btn('newparcel','＋ Registrar parcela')}${btn('newproducer','＋ Registrar productor')}${btn('print','Imprimir resumen')}</section><div class="metrics">${metric('Productores y entidades',data.producers.filter(x=>x.activo).length)}${metric('Parcelas monitoreadas',data.parcels.length)}${metric('Avisos sin acuse',data.alerts.filter(x=>!x.ack).length)}${metric('Municipios',new Set(data.parcels.map(p=>p.zone)).size)}</div><div class="grid"><div>${card('Red de parcelas','<div id="map" class="map"></div><small>Selecciona un marcador para ver sus lecturas. Los puntos precargados corresponden a centros agrícolas documentados.</small>',badge('Bolivia'))}${card('Temperatura registrada',lineplot(h)+`<small>${h.length} registros de modelo · ${esc(p?.zone)} · °C</small>`)}</div><div>${choose()}${climateCard()}${card('Actividad reciente',last.map(x=>`<div class="log">${esc(x.accion)}<small>${stamp(x.fecha)}</small></div>`).join(''))}</div></div><p class="hint note"><b>Origen de la precarga.</b> Las lecturas meteorológicas provienen de Open-Meteo. Las fichas públicas identifican centros agrícolas y cultivos documentados. La etapa actual y el alta de sus titulares quedan sin verificar.</p>`;
}
function controls(){return `<div class="tools"><input id="search" aria-label="Buscar" placeholder="Buscar por nombre, zona o cultivo" value="${esc(search)}"><select id="filter" aria-label="Filtro de origen">${opts(['Todos','Referencia pública','Registrado'],status)}</select></div>`}
const match=(x,txt)=>(status==='Todos'||(status==='Referencia pública')===!!x.ejemplo)&&txt.toLocaleLowerCase().includes(search.toLocaleLowerCase());
function whatsappDirectory(){
 return '<p><a href="/cuaderno#whatsapp">Ver registros de WhatsApp (Equipo) →</a></p>';
}
function producers(){
 const list=data.producers.filter(x=>match(x,x.nombre+' '+x.comunidad));
 return title('Productores','Directorio, contacto e historial de actividad.',btn('newproducer','＋ Nuevo productor','','primary'))+whatsappDirectory()+card('Directorio',controls()+table(['Productor','Comunidad','Parcelas','Estado','Origen','Acciones'],list.map(x=>`<tr><td><b>${esc(x.nombre)}</b><br>${esc(x.telefono||'Sin teléfono')}</td><td>${esc(x.comunidad)}</td><td>${data.parcels.filter(p=>p.productor===x.id).length}</td><td>${badge(x.activo?'Activo':'Inactivo')}</td><td>${x.ejemplo?'Referencia pública':'Registrado'}</td><td>${btn('producer','Ficha',x.id)} ${x.activo&&!x.ejemplo?btn('editproducer','Editar',x.id):''}</td></tr>`).join('')));
}
function parcels(){
 const list=data.parcels.filter(x=>match(x,x.name+' '+x.zone+' '+x.crop+' '+(producer(x.productor)?.nombre||'')));
 return title('Parcelas','Catastro agrícola y estado de monitoreo.',btn('newparcel','＋ Nueva parcela','','primary'))+whatsappDirectory()+card('Parcelas monitoreadas',controls()+table(['Parcela / origen','Productor','Cultivo','Área','Municipio','Riesgo','Acciones'],list.map(x=>`<tr><td><b>${esc(x.name)}</b><br><small>${x.ejemplo?'Referencia pública':'Registrada'}</small></td><td>${esc(producer(x.productor)?.nombre||'Perfil del cuaderno')}</td><td>${esc(x.crop)}</td><td>${f(x.area)} ha</td><td>${esc(x.zone)}</td><td>${badge(parcelLevel(x.number))}</td><td>${btn('meteo','Clima',x.number)} ${x.ejemplo?btn('source','Fuentes',x.number):btn('editparcel','Editar',x.number)}</td></tr>`).join('')))+(data.archived.length?card('Parcelas archivadas',data.archived.map(x=>`<div class="line log">${esc(x.name)} · ${esc(x.zone)} ${btn('archhistory','Ver historial',x.number)}</div>`).join('')):'');
}
function weather(){
 const p=current(),w=p?.weather,hh=detail?.history||[];
 return title('Meteorología','Series del modelo, hora local y pronóstico.',btn('csv','Exportar historial CSV'))+choose()+`<div class="grid"><div>${climateCard()}</div><div>${card('Tendencia de temperatura',lineplot(hh.slice().reverse().filter(x=>x.temp!=null))+'<small>Historial del modelo en °C · America/La_Paz</small>')}</div></div>`+card('Pronóstico diario',table(['Fecha','Mín. °C','Máx. °C','Precip. mm','Prob. lluvia','Ráfaga km/h'],(w?.days||[]).map(x=>`<tr><td>${x.date}</td><td>${f(x.low)}</td><td>${f(x.high)}</td><td>${f(x.rain)}</td><td>${f(x.prob)} %</td><td>${f(x.gust)}</td></tr>`).join('')))+card('Últimas lecturas',table(['Fecha y hora','°C','Humedad %','Lluvia mm','Viento km/h','Dirección °'],hh.slice(0,24).map(x=>`<tr><td>${stamp(x.hora)}</td>${['temp','hum','lluvia','viento','direccion'].map(k=>'<td>'+f(x[k])+'</td>').join('')}</tr>`).join('')));
}
const riskRow=r=>`<div class="riskbox"><div class="line"><h3>${esc(r.kind)}</h3>${badge(alertLevel(r.kind))}</div><small>${esc(r.date||r.day)}</small><p>${esc(r.evidence)}</p><b>Orientación</b> · ${esc(r.action)}</div>`;
function riskView(){
 const ev=detail?.evaluations||[],last=ev[0],active=last?JSON.parse(last.resultado):[];
 return title('Evaluación de riesgos','Evidencia y recomendaciones por cultivo y etapa.')+choose()+card('Última evaluación registrada',`<p>${esc(last?.contexto||'Sin evaluación')} · ${stamp(last?.hora)}</p>${last&&!active.length?badge('Bajo')+' Ningún umbral superado.':active.map(riskRow).join('')}<p class="hint">Umbrales experimentales para este piloto. La probabilidad de lluvia es una variable del pronóstico.</p>`)+card('Historial de evaluaciones',table(['Fecha del modelo','Cultivo y etapa','Eventos detectados'],ev.map(x=>`<tr><td>${stamp(x.hora)}</td><td>${esc(x.contexto)}</td><td>${JSON.parse(x.resultado).length}</td></tr>`).join('')));
}
function alertView(){
 const a=detail?.alerts||[],n=detail?.notifications||[];
 return title('Alertas y notificaciones','Avisos activos, atendidos y vencidos de la parcela.')+choose()+(detail?.failures?.length?card('Seguimiento de envíos',detail.failures.map(x=>`<div class="log">Aviso #${x.alerta} · ${esc(x.estado)} · Intentos fallidos: ${x.intentos}<small>${stamp(x.fecha)}</small></div>`).join('')):'')+card('Historial de avisos',a.map(x=>`<article class="riskbox"><div class="line"><b>${esc(x.kind)} · ${esc(x.day)}</b>${badge(x.estado)}</div><p>${esc(x.evidence)}. ${esc(x.action)}</p><small>${esc(x.source)} · ${stamp(x.stamp)}</small> ${x.estado==='Activa'?btn('ack','Acusar recibo',x.id):''}</article>`).join('')||'<p>Sin avisos registrados.</p>')+card('Bitácora de notificaciones',n.map(x=>`<div class="log"><b>${esc(x.channel)}</b> · ${esc(x.status||'Publicada en el panel')}<p>${esc(x.body)}</p><small>${stamp(x.stamp)}</small></div>`).join('')||'<p>Aún no hay notificaciones.</p>',current()&&!current().ejemplo?btn('link','Vincular WhatsApp'):'' );
}
function lab(){
 return title('Laboratorio climático','Compara un escenario adverso con la última lectura de una parcela.')+choose()+`<div class="grid"><div>${card('Configurar ensayo',`<form id="lab" class="form">${select('scene','Fenómeno',['Helada','Lluvia intensa','Déficit de lluvia','Calor extremo','Aire seco','Viento fuerte'],attempt?.scene)}${input('factor','Intensidad de la perturbación',attempt?.factor||1,'number','min=".25" max="2" step=".25" required')}<button class="primary">Evaluar y probar notificación</button></form>`)}</div><div>${card('Resultado comparado',attempt?resultBlock(attempt):'<p>Elige un fenómeno para evaluar las mismas reglas con condiciones modificadas.</p>')}</div></div>`+card('Ensayos guardados',data.runs.map(x=>`<div class="line log"><span>${esc(x.parcela)} · ${esc(x.escenario)}<small>${stamp(x.fecha)}</small></span>${btn('run','Abrir',x.id)}</div>`).join('')||'<p>Aún no se registraron ensayos.</p>');
}
function resultBlock(r){return `<p>${badge('Simulación')} · Ensayo #${r.id} · Nivel ${esc(r.level)}</p>${table(['Variable','Base','Escenario'],[['Mínima °C',r.baseline.low,r.scenario.low],['Máxima °C',r.baseline.high,r.scenario.high],['Lluvia mm',r.baseline.rain,r.scenario.rain],['Ráfaga km/h',r.baseline.gust,r.scenario.gust],['Humedad %',...r.humidity],['Avisos en 7 días',r.before.length,r.after.length]].map(([t,a,b])=>`<tr><td>${t}</td><td>${f(a)}</td><td>${f(b)}</td></tr>`).join(''))}<div class="notice"><b>Notificación de prueba</b> · <a href="/whatsapp" target="_blank" rel="noopener">Ver en el chat del productor ↗</a><p>${esc(r.notice)}</p>${r.delivery?`<small>Buzón de prueba · ${esc(r.delivery.destinatario)} · Recibida ${stamp(r.delivery.recibido)}</small><div>${r.delivery.acuse?badge('Acusada'):btn('simack','Confirmar recepción de prueba',r.id)}</div>`:''}</div><small>Base · ${esc(r.source)} · ${stamp(r.valid)}</small>`}
function render(){
 if(map){map.remove();map=null}
 $('#nav').innerHTML=Object.entries(nav).map(([t,ic])=>`<button data-a="nav" data-v="${t}" class="${tab===t?'active':''}"><span>${ic}</span>${t}</button>`).join('');
 $('#screen').innerHTML=({'Resumen':dashboard,'Productores':producers,'Parcelas':parcels,'Meteorología':weather,'Riesgos':riskView,'Alertas':alertView,'Laboratorio':lab})[tab]();
 if($('#map')){
  map=L.map('map',{scrollWheelZoom:false}).setView([-17,-67],7);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',maxZoom:19}).addTo(map);
  const bounds=[];for(const p of data.parcels){bounds.push([p.lat,p.lon]);L.circleMarker([p.lat,p.lon],{radius:p.number===selected?10:7,weight:2,color:'#fff',fillColor:parcelLevel(p.number)==='Alto'?'#a95539':'#397253',fillOpacity:1}).addTo(map).bindTooltip(esc(p.name)).on('click',()=>setParcel(p.number))}
  if(bounds.length)map.fitBounds(bounds,{padding:[20,20],maxZoom:11});
 }
 if($('#choice'))$('#choice').onchange=e=>setParcel(Number(e.target.value));
 if($('#search'))$('#search').oninput=e=>{search=e.target.value;render();$('#search').focus();$('#search').setSelectionRange(search.length,search.length)};
 if($('#filter'))$('#filter').onchange=e=>{status=e.target.value;render()};
}
async function loadDetail(){const seq=++detailRequest,n=selected;const out=n?await api('atlas/history?number='+n):null;if(seq===detailRequest&&selected===n)detail=out}
async function setParcel(n){selected=n;detail=null;attempt=null;await loadDetail();render()}
async function sync(){
 data=await api('atlas');if(!data.parcels.some(x=>x.number===selected))selected=data.parcels[0]?.number||0;
 await loadDetail();render();$('#sync').textContent='● Sincronizado · '+new Date().toLocaleTimeString('es-BO',{timeZone:'America/La_Paz'});
}
function producerForm(x={},parcelDraft=null){
 displayDialog(`<h2>${x.id?'Editar':'Registrar'} productor</h2><form id="producer" class="form">${parcelDraft?'<p>Al guardar el titular volverás a tu parcela.</p>':''}<input type="hidden" name="id" value="${x.id||''}">${input('nombre','Nombre completo',x.nombre,'text','required maxlength="100"')}${input('telefono','Teléfono de contacto',x.telefono,'tel')}${input('comunidad','Zona o comunidad',x.comunidad,'text','required')}<label>Actividad y observaciones<textarea name="notas">${esc(x.notas)}</textarea></label><button class="primary">Guardar productor</button>${x.id?btn('archiveP','Desactivar productor',x.id):''}<div class="error"></div></form>`);
 $('#producer').parcelDraft=parcelDraft;
}
function parcelForm(x={}){
 const ps=data.producers.filter(z=>z.activo&&!z.ejemplo);
 displayDialog(`<h2>${x.number?'Editar':'Registrar'} parcela</h2><form id="parcel" class="form"><input type="hidden" name="number" value="${x.number||''}">${input('name','Nombre de parcela',x.name,'text','required')}<label>Productor<select required name="productor">${ps.length?'':'<option value="">Registra el titular para continuar</option>'}${ps.map(z=>`<option value="${z.id}" ${z.id===x.productor?'selected':''}>${esc(z.nombre)}${z.ejemplo?' · Referencia pública':''}</option>`).join('')}</select></label>${btn('addOwner','＋ Registrar nuevo titular')}${select('zone','Municipio',Object.keys(data.zones),x.zone||'Viacha')}<div class="pair">${select('crop','Cultivo',data.crops,x.crop)}${select('stage','Etapa',data.stages,x.stage)}</div><div class="pair">${input('lat','Latitud',x.lat??-16.65,'number','step="any" min="-90" max="90" required')}${input('lon','Longitud',x.lon??-68.30,'number','step="any" min="-180" max="180" required')}</div><small>Se proponen coordenadas municipales. Ingresa las de tu terreno.</small><div class="pair">${input('area','Superficie (ha)',x.area,'number','step="any" min=".000001" required')}${input('altitud','Altitud (m)',x.altitud,'number','step="any"')}</div>${input('caracteristicas','Características del terreno',x.caracteristicas)}<label class="check"><input type="checkbox" name="consent" required> Autorizo el registro y monitoreo de esta parcela.</label><button class="primary">Guardar parcela</button>${x.number?btn('archiveL','Desactivar parcela',x.number):''}<div class="error"></div></form>`);
 $('#parcel').elements.consent.checked=Boolean(x.consent);
 $('#parcel select[name=zone]').onchange=e=>{const f=$('#parcel').elements;[f.lat.value,f.lon.value]=data.zones[e.target.value]};
}
async function action(a,v){
 if(a==='print')window.print();
 if(a==='archhistory'){const h=await api('atlas/history?number='+v);displayDialog('<h2>Historial de parcela archivada</h2><p>'+h.history.length+' lecturas en la consulta · '+h.evaluations.length+' evaluaciones</p>'+h.alerts.map(riskRow).join(''))}
 if(a==='nav'){tab=v;search='';status='Todos';render();scrollTo(0,0)}
 if(a==='addOwner'){
  const form=$('#parcel');
  const draft=Object.fromEntries(new FormData(form));
  draft.consent=form.elements.consent.checked;
  producerForm({},draft);
 }
 if(a==='newproducer'||a==='editproducer')producerForm(producer(+v));
 if(a==='newparcel'||a==='editparcel')parcelForm(data.parcels.find(x=>x.number===+v));
 if(a==='producer'){const p=producer(+v);displayDialog(`<h2>${esc(p.nombre)}</h2><p>${esc(p.comunidad)} · ${esc(p.telefono||'Sin teléfono')}</p><p>${esc(p.notas)}</p><h3>Historial</h3>${data.audit.filter(x=>x.productor===p.id).map(x=>`<div class="log">${esc(x.accion)}<small>${stamp(x.fecha)}</small></div>`).join('')}`)}
 if(a==='meteo'){tab='Meteorología';await setParcel(+v)}
 if(a==='refresh'){await api('ops/refresh',{number:selected});await sync();toast('Lectura actualizada')}
 if(a==='ack'){await api('ops/ack',{number:selected,alert:+v});await sync();toast('Acuse guardado')}
 if(a==='archiveP'||a==='archiveL'){if(!confirm('¿Desactivar el registro y detener el monitoreo asociado? Se conserva su historial.'))return;await api('atlas/archive',a==='archiveP'?{id:+v}:{number:+v});$('dialog').close();await sync()}
 if(a==='source'){const p=data.parcels.find(x=>x.number===+v),r=data.catalog.find(x=>x.name===p.name);displayDialog(`<h2>${esc(p.name)}</h2><p>${esc(p.caracteristicas)}</p><p>Latitud ${p.lat} · Longitud ${p.lon} · ${f(p.altitud)} m</p><p>Superficie documentada: ${f(p.area)} ha</p>${(r?.sources||[]).map((u,i)=>`<p><a href="${esc(u)}" target="_blank" rel="noopener">Consultar fuente documental ${i+1} ↗</a></p>`).join('')}`)}
 if(a==='simack'){await api('atlas/sim-ack',{id:+v});const r=await api('atlas/run?id='+v);if(attempt?.id===r.id)attempt={...attempt,...r};displayDialog('<h2>Recepción registrada</h2>'+resultBlock(r));render()}
 if(a==='run'){const r=await api('atlas/run?id='+v);displayDialog('<h2>Ensayo guardado</h2>'+resultBlock({...r,id:+v}))}
 if(a==='link'){const r=await api('atlas/link',{number:selected});displayDialog(`<h2>Vincular al productor</h2><p>Desde el número con alta en Yapu, envía <strong>VINCULAR ${esc(r.code)}</strong> al WhatsApp del proyecto. El código vence en 15 minutos.</p>`)}
 if(a==='csv'){const fields=['hora','fuente','temp','hum','lluvia','viento','direccion'],h=detail?.history||[];const rows=[fields.join(';'),...h.map(x=>fields.map(k=>'"'+String(x[k]??'').replaceAll('"','""')+'"').join(';'))];const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.join('\r\n')],{type:'text/csv;charset=utf-8'}));const b=document.createElement('a');b.href=url;b.download='clima-parcela-'+selected+'.csv';b.click();setTimeout(()=>URL.revokeObjectURL(url),5000)}
}
document.addEventListener('click',async e=>{const b=e.target.closest('[data-a]');if(!b)return;b.disabled=true;busy=true;try{await action(b.dataset.a,b.dataset.v)}catch(err){toast(err.message)}finally{busy=false;b.disabled=false}});
document.addEventListener('submit',async e=>{
 e.preventDefault();const form=e.target,b=form.querySelector('button:not([type=button])');if(b.disabled)return;b.disabled=true;busy=true;const d=Object.fromEntries(new FormData(form));
 try{
 if(form.getAttribute('id')==='producer'){
  const owner=await api('atlas/producer',d);
  await sync();
  if(form.parcelDraft){parcelForm({...form.parcelDraft,productor:owner.id});toast('Titular guardado. Completa la parcela.')}
  else{$('dialog').close();toast('Productor guardado')}
 }
 if(form.getAttribute('id')==='parcel'){d.consent=form.elements.consent.checked;const r=await api('atlas/parcel',d);selected=r.number;$('dialog').close();await sync();toast('Parcela guardada. Consultando el clima…');try{await api('ops/refresh',{number:r.number});await sync()}catch{toast('Parcela guardada. La actualización del clima queda pendiente.')}}
 if(form.getAttribute('id')==='lab'){attempt={...await api('atlas/simulate',{...d,number:selected}),...d};await sync()}
 }catch(err){const el=form.querySelector('.error');if(el)el.textContent=err.message;toast(err.message)}finally{busy=false;b.disabled=false}
});
$('.close').onclick=()=>$('dialog').close();
async function watch(){let seen=0;while(true){try{const v=await api('ops/wait?seen='+seen);if(document.hidden||busy||$('dialog').open||['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)){await new Promise(r=>setTimeout(r,2000));continue}if(v.version!==seen){await sync();seen=v.version}}catch(e){$('#sync').textContent='Reconectando al servidor…';await new Promise(r=>setTimeout(r,4000));try{await sync()}catch{}}}}
sync().then(watch).catch(e=>{$('#screen').textContent=e.message;$('#sync').textContent='Error de carga · vuelve a abrir el panel'});
