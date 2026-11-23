'use strict';
const $=s=>document.querySelector(s);
const h=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const opts=(arr,v)=>arr.map(x=>`<option ${x===v?'selected':''}>${h(x)}</option>`).join('');
const field=(key,title,arr,v)=>`<label>${title}<select name="${key}">${opts(arr,v)}</select></label>`;
const formData=f=>Object.fromEntries(new FormData(f));
const btn=(action,label,cls='ghost',arg='')=>`<button type="button" class="${cls}" data-do="${action}" data-arg="${h(arg)}">${label}</button>`;
const title=(tag,name,extra='')=>`<div class="titlebar"><div><div class="eyebrow">${tag}</div><h1>${name}</h1></div>${extra}</div>`;
const tabs=['Mi parcela','Asistente','Alertas','Laboratorio','Mercado'];
let s,page='Monitor',day=0,adminKey='',adm,filter='Todas',timer;
const dlabel=(date,len='short')=>new Date(date+'T12:00:00').toLocaleDateString('es-BO',{weekday:len,day:'numeric'});
function notify(msg){$('#toast').textContent=msg;clearTimeout(timer);timer=setTimeout(()=>$('#toast').textContent='',4500)}
function teamHeaders(){
 return adminKey ? {'X-Yapu-Admin-UTF8':encodeURIComponent(adminKey)} : {};
}
async function api(path,data){
 const r=await fetch('/api/'+path,{method:data?'POST':'GET',headers:{'Content-Type':'application/json',...teamHeaders()},body:data?JSON.stringify(data):undefined});
 const j=await r.json();if(!r.ok)throw Error(j.error||'No se completó la operación');return j;
}
async function refresh(){s=await api('state');render()}
function modal(html){$('#modal').innerHTML=html;const dlg=$('#dialog');if(!dlg.open)dlg.showModal()}
function closeModal(){$('#dialog').close()}
function profileForm(scene=s.profile.scene){
 const p=s.profile;
 modal(`<h2>Configurar parcela</h2><form id="profile" class="form"><label>Nombre de la parcela<input name="name" maxlength="60" required value="${h(p.name)}"></label><div class="two">${field('zone','Municipio',s.zones,p.zone)}${field('crop','Cultivo',s.crops,p.crop)}</div>${field('stage','Etapa del cultivo',s.stages,p.stage)}<label>Origen del clima<select name="mode"><option value="demo" ${p.mode==='demo'?'selected':''}>Demostración sin internet</option><option value="live" ${p.mode==='live'?'selected':''}>Pronóstico en línea · Open-Meteo</option></select></label>${field('scene','Escenario de demostración',s.scenes,scene)}<label class="check"><input type="checkbox" name="consent" required ${p.consent?'checked':''}>Acepto guardar mi parcela, historial y observaciones. Si el equipo habilita IA externa, se puede procesar la orientación recuperada.</label><button>Guardar parcela</button>${p.consent?btn('delete','Eliminar mis datos','link'):''}<div class="error"></div></form>`);
}
function graph(days){
 const hi=Math.max(...days.map(x=>x.high))+2,lo=Math.min(...days.map(x=>x.low))-2,y=n=>96-(n-lo)*86/(hi-lo);
 const pts=k=>days.map((d,i)=>`${20+i*90},${y(d[k])}`).join(' ');
 return `<svg class="chart" viewBox="0 0 580 106" preserveAspectRatio="none" role="img" aria-label="Curvas de temperatura máxima y mínima de siete días"><path d="M20 16H560 M20 54H560 M20 92H560" stroke="#dce1d4" stroke-dasharray="4 5"/><polygon points="${pts('high')} ${days.map((_,j)=>{let i=6-j;return (20+i*90)+','+y(days[i].low)}).join(' ')}" fill="#e5ecda"/><polyline points="${pts('high')}" fill="none" stroke="#a87531" stroke-width="3"/><polyline points="${pts('low')}" fill="none" stroke="#487563" stroke-width="3"/>${['high','low'].map(k=>`<circle cx="${20+day*90}" cy="${y(days[day][k])}" r="4" fill="#224c3c"/>`).join('')}</svg>`;
}
function chartCard(){
 if(!s.weather)return `<div class="card"><h2>Pronóstico sin datos</h2><p>${h(s.error)}</p>${btn('refresh','Reintentar')}</div>`;
 const ds=s.weather.days,d=ds[day];
 return `<section class="card"><div class="heading"><h2>Los próximos siete días</h2><span class="pill">${s.profile.mode==='demo'?'Simulado':'Open-Meteo'}</span></div><div class="days">${ds.map((x,i)=>btn('day',`<b>${h(dlabel(x.date))}</b><span>${x.low<=1?'❄':x.rain>=20?'☂':x.code===96?'ϟ':'☼'}</span>${x.high}° / ${x.low}°`,i===day?'selected':'',i)).join('')}</div>${graph(ds)}<b>${h(dlabel(d.date,'long'))}</b><div class="details">Máx. ${d.high} °C · Mín. ${d.low} °C · Lluvia ${d.rain} mm · Ráfagas ${d.gust} km/h</div><small>${h(s.weather.source)} · Consulta ${h(s.weather.stamp.replace('T',' '))}</small></section>`;
}
function home(){
 const p=s.profile, r=s.risks[0],w=s.weather;
 return `<section class="hero"><span class="eyebrow">Cuaderno de campo &nbsp; / &nbsp; La Paz</span><h1>${h(p.name)}</h1><p>${h(p.zone)} &nbsp;·&nbsp; ${h(p.crop)} en ${h(p.stage.toLowerCase())}</p>${btn('profile','Configurar parcela ↗','')}</section><div class="stats">${[['Mínima hoy',w?w.days[0].low+' °C':'—'],['Lluvia hoy',w?w.days[0].rain+' mm':'—'],['Días con alerta',w?new Set(s.risks.map(x=>x.date)).size+' / 7':'—']].map(([k,v])=>`<div class="stat"><small>${k}</small><strong>${v}</strong></div>`).join('')}</div><div class="grid">${chartCard()}<section class="card side"><div class="eyebrow">Lectura de la parcela</div><h2 style="margin-top:10px">${r?'Atención a '+h(r.kind.toLowerCase()):w?'Semana sin avisos':'Pendiente de pronóstico'}</h2><p>${r?h(r.evidence)+' el '+h(dlabel(r.date))+'. '+h(r.action):w?'Los valores se mantienen dentro de los umbrales del piloto.':'Reintenta la consulta para evaluar los umbrales.'}</p><small>Orientación piloto · ${p.mode==='demo'?'Datos simulados':'Pronóstico sujeto a cambios'}</small><div class="sep">${btn('go','Consultar al asistente →','',tabs[1])} ${r?btn('card','Descargar aviso PNG','link'):''}</div></section></div>`;
}
function assistant(){
 return title('Agente agrícola','Asistente de campo',`<span class="pill">${s.used} / ${s.plans[s.profile.plan]} consultas hoy</span>`)+`<div class="grid"><section class="card"><h2>Conversación</h2><small>${h(s.ctx)}</small><div class="conversation">${s.chat.length?s.chat.map(m=>`<div class="bubble question">${h(m.q)}</div><div class="bubble">${h(m.a)}</div>`).join(''):'<p class="muted">Pregunta por tu cultivo o por el pronóstico de tu parcela.</p>'}</div><form id="chat" class="form"><label>Tu consulta<textarea name="q" maxlength="800" required placeholder="¿Hay riesgo de helada esta semana?"></textarea></label><div class="actions"><button>Enviar consulta →</button>${btn('dictate','Dictar')}${s.chat.length?btn('speak','Escuchar respuesta'):''}</div><div class="error"></div></form></section><aside class="card side"><div class="eyebrow">Preguntas para empezar</div><div class="list chips" style="margin:16px 0">${['¿Hay riesgo de helada?','¿Cómo reviso la humedad del suelo?','Mi cultivo tiene manchas, ¿qué hago?'].map(q=>btn('prompt',q,'ghost',q)).join('')}</div><div class="sep">${btn('channel','Probar canal WhatsApp ↗','')}</div><div class="sep"><h3>Revisión técnica</h3>${s.cases.length?s.cases.map(x=>`<div class="entry"><small>Caso #${x.id} · ${h(x.status)}</small><p>${h(x.question)}</p></div>`).join(''):'<p class="tip">Las consultas que necesitan evaluación en campo aparecerán aquí.</p>'}</div></aside></div>`;
}
function alerts(){
 const items=s.alerts.filter(x=>filter==='Todas'||(filter==='Pendientes'?x.occurred===null:x.occurred!==null));
 return title('Seguimiento','Bitácora de alertas')+`<div class="row chips">${['Todas','Pendientes','Evaluadas'].map(t=>btn('filter',t,t===filter?'selected':'ghost',t)).join('')}</div><div class="statusline">Historial de escenarios y pronósticos de esta parcela. Registra la observación cuando termine el periodo previsto.</div><div class="list">${items.map(x=>`<article class="card"><div class="heading"><h3>${h(x.kind)} · ${h(dlabel(x.day))}</h3><span class="pill ${x.occurred===null?'warm':''}">${x.occurred===null?'Sin evaluar':'Evaluada'}</span></div><small>${h(x.ctx)} · ${h(x.source)}</small><p><b>${h(x.evidence)}</b>. ${h(x.action)}</p><small>Consulta ${h(x.stamp)} · Umbral experimental, sujeto al microclima local.</small><div class="actions sep">${btn('feedback',x.occurred===null?'Registrar observación':'Editar observación','ghost',x.id)}${x.occurred!==null?`<small>Ocurrió: ${x.occurred?'sí':'no'} · Fue útil: ${x.useful?'sí':'no'}</small>`:''}</div></article>`).join('')||'<div class="card">No hay alertas con este filtro.</div>'}</div>`;
}
function lab(){
 return title('Exploración guiada','Laboratorio climático')+`<div class="grid"><section class="card"><h2>Ensaya una semana</h2><p>Elige un fenómeno y observa qué regla se activa para tu cultivo. La vista previa utiliza siete días sintéticos.</p><div class="form">${field('labscene','Fenómeno',s.scenes,s.profile.scene)}${field('labcrop','Cultivo',s.crops,s.profile.crop)}${field('labstage','Etapa',s.stages,s.profile.stage)}${btn('simulate','Evaluar escenario →','')}</div></section><section class="card side" id="labresult"><div class="eyebrow">Resultado del ensayo</div><h2 style="margin-top:12px">Datos → regla → acción</h2><p>Evalúa un escenario para ver la evidencia, el umbral y la orientación que recibiría el productor.</p></section></div>`;
}
async function refreshRegistrations(){
 const panel=$('#wa-registrations');
 if(!panel || panel.dataset.loading)return;
 panel.dataset.loading='1';
 try{
  const {registrations}=await api('admin/whatsapp');
  panel.innerHTML=registrations.length?registrations.map(x=>`<div class="entry"><strong>WhatsApp · •••• ${h(x.ending)}</strong><p>${h(x.zone)} · ${h(x.crop)} · ${h(x.stage)}</p></div>`).join(''):'<p>Todavía no hay altas confirmadas desde WhatsApp.</p>';
 }catch(e){panel.textContent='No se pudieron consultar las altas. '+e.message}
 finally{delete panel.dataset.loading}
}
setInterval(()=>{if(page==='Equipo' && !document.hidden)refreshRegistrations()},5000);
function adminPage(){
 const st=adm.stats;
 return title('Acceso del equipo','Administración',btn('go','Abrir monitor del equipo','', 'Monitor')+' '+btn('logout','Cerrar acceso'))+`<section class="card"><h2>Productores de WhatsApp</h2><p>Altas confirmadas con su municipio, cultivo y etapa.</p><div id="wa-registrations">Consultando altas…</div></section><div class="stats">${[['Parcelas',adm.users.length],['Alertas evaluadas',st.responses+' / '+st.alerts],['Útiles según productor',st.responses?Math.round(st.useful/st.responses*100)+' %':'Sin datos']].map(([k,v])=>`<div class="stat"><small>${k}</small><strong>${v}</strong></div>`).join('')}</div><p class="tip">Incluye demostraciones. Coincidencias reportadas: ${st.occurred||0} de ${st.responses} evaluaciones. Estas observaciones no miden la precisión en campo por sí solas.</p><div class="grid"><section class="card"><div class="heading"><h2>Base de conocimiento</h2>${btn('doc','Añadir ficha')}</div>${adm.docs.map(x=>`<div class="entry"><b>${h(x.title)}</b><p>${h(x.body)}</p><small>${h(x.crop)} · ${h(x.source)} &nbsp; </small>${btn('doc','Editar','link',x.id)}</div>`).join('')}</section><div><section class="card"><h2>Productores y planes</h2><p class="tip">Gratuito · Productor Bs 20/mes · Asociación Bs 400/mes por grupo de hasta 50 socios.</p>${adm.users.map(x=>`<form class="entry form plan" data-id="${x.number}"><strong>#${x.number} · ${h(x.name)}</strong><small>${h(x.zone)} · ${h(x.crop)}</small>${field('plan','Plan',Object.keys(s.plans),x.plan)}<button>Aplicar plan</button></form>`).join('')}</section><section class="card stack"><h2>Cola de revisión</h2>${adm.cases.map(x=>`<div class="entry"><small>#${x.id} · ${h(x.name)} · ${x.status}</small><p>${h(x.question)}</p>${btn('case',x.status==='Pendiente'?'Marcar revisado':'Reabrir','ghost',x.id)}</div>`).join('')||'<p>Sin casos pendientes.</p>'}</section></div></div>`;
}
const money=c=>(c/100).toLocaleString('es-BO',{minimumFractionDigits:2,maximumFractionDigits:2})+' Bs';
function market(){
 const item=o=>{const act=(a,t)=>btn('trade',t,'ghost',o.id+'|'+a);
 return `<article class="card"><div class="heading"><h3>${h(o.crop)} · ${h(o.zone)}</h3><span class="pill">${h(o.status)}</span></div><p>${h(o.description)}</p><strong>${money(o.cents)}</strong><p class="tip">${o.mine?'Tu oferta':o.buying?'Tu compra':'Oferta disponible'} · Lote #${o.id}</p><div class="actions">${o.status==='Abierta'?(o.mine?act('withdraw','Retirar oferta'):act('reserve','Reservar lote')):o.status==='Reservada'?(o.mine&&o.seller_ok||o.buying&&o.buyer_ok?'<span class="pill">Confirmación enviada</span>':act('confirm','Confirmar venta realizada'))+act('cancel','Cancelar reserva'):''}</div>${o.status==='Confirmada'?`<p>Ambas partes confirmaron. Comisión del vendedor: <b>${money(o.fee)}</b>.</p>`:''}</article>`};
 return title('Intercambio local','Mercado de cosechas',btn('offer','Publicar un lote +',''))+`<p class="statusline">Piloto de compraventa. El monto corresponde al lote completo. La comisión del 2 % se registra al confirmar ambas partes. Los pagos se realizan fuera del sistema.</p><div class="list">${s.market.map(item).join('')||'<div class="card"><h2>Aún no hay lotes</h2><p>Publica un lote para iniciar el intercambio. Usa dos navegadores independientes para representar al vendedor y al comprador durante la demostración.</p></div>'}</div>`;
}
function offer(){
 if(!s.profile.consent){profileForm();notify('Guarda tu parcela antes de publicar.');return}
 modal(`<h2>Publicar lote</h2><form id="offer" class="form">${field('crop','Cultivo',s.crops,s.profile.crop)}<label>Descripción y cantidad<input name="description" maxlength="160" required placeholder="Ej. 5 quintales de papa, entrega en Viacha"></label><label>Precio total en bolivianos<input name="price" type="number" step=".01" min=".01" max="10000000" required></label><small>El municipio y la descripción serán visibles en el mercado. Evita incluir datos personales.</small><button>Publicar</button><div class="error"></div></form>`);
}
function downloadCard(){
 const r=s.risks[0],cv=document.createElement('canvas');cv.width=1000;cv.height=660;const g=cv.getContext('2d');g.fillStyle='#1e493a';g.fillRect(0,0,1000,660);
 let y=70;function line(t,size,color,width=865){g.fillStyle=color;g.font=size+'px Georgia';let txt='';for(const word of t.split(' ')){if(g.measureText(txt+' '+word).width>width){g.fillText(txt,55,y);y+=size*1.3;txt=word}else txt+=(txt?' ':'')+word}g.fillText(txt,55,y);y+=size*1.45}
 line('YAPU IA    /    CUADERNO DE CAMPO',24,'#eec480');line(r.kind,68,'#fff8e9');line(s.ctx,29,'#dee9d5');line(r.date+' · '+r.evidence,28,'#fff8e9');line(r.action,32,'#fff8e9');y+=14;line('Fuente: '+s.weather.source+' · '+s.weather.stamp,21,'#eec480');line('Orientación piloto. Las condiciones de la parcela pueden variar.',21,'#eec480');
 const a=document.createElement('a');a.download='YapuIA-alerta-'+r.date+'.png';a.href=cv.toDataURL('image/png');a.click();
}

function render(){
 document.body.classList.toggle('station',page==='Monitor');
 stopMonitor();
 $('nav').innerHTML=['Monitor',...tabs].map(t=>btn('go',t,page===t?'active':'',t)).join('');
 if(page==='Monitor'){startMonitor();return}
 $('#app').innerHTML=page==='Equipo'?adminPage():[home,assistant,alerts,lab,market][tabs.indexOf(page)]();
 const cv=$('.conversation');if(cv)cv.scrollTop=cv.scrollHeight;
}
async function team(){adm=await api('admin');page='Equipo';render();await refreshRegistrations()}
function login(){modal(`<img class="logo" src="/marca.png" alt="Yapu IA"><h2>Acceso del equipo</h2><p>Ingresa la clave que muestra el servidor al iniciar.</p><form id="login" class="form"><label>Clave de administración<input name="key" type="password" required></label><button>Entrar al panel</button><div class="error"></div></form>`)}
async function action(a,v){
 if(a==='go'){page=v;if(v==='Monitor')render();else await refresh();window.scrollTo(0,0)}
 if(a==='channel'){modal(`<h2>WhatsApp de prueba</h2><p class="tip">Simulador local. El alta se guarda en un perfil de prueba independiente. No envía mensajes a teléfonos.</p><div class="conversation" id="channelLog"><div class="bubble">Para registrar tu parcela, acepta el uso de tus datos de prueba enviando ALTA Viacha/Papa/Floración. Luego puedes consultar el pronóstico.</div></div><form id="channel" class="form"><label>Mensaje<input name="text" required maxlength="800" value="ALTA Viacha/Papa/Floración"></label><button>Enviar mensaje</button><div class="error"></div></form>`)}
 if(a==='offer')offer();
 if(a==='card')downloadCard();
 if(a==='trade'){const [id,action]=v.split('|');if(!confirm('¿Registrar esta acción sobre el lote #'+id+'?'))return;await api('market',{id:Number(id),action});await refresh()}
 if(a==='profile')profileForm();
 if(a==='day'){day=Number(v);render()}
 if(a==='refresh')await refresh();
 if(a==='filter'){filter=v;render()}
 if(a==='prompt'){const t=$('[name=q]');t.value=v;t.focus()}
 if(a==='speak'){if(!window.speechSynthesis)throw Error('Tu navegador no admite lectura en voz alta.');speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(s.chat.at(-1).a);u.lang='es-BO';speechSynthesis.speak(u)}
 if(a==='dictate'){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R)throw Error('El dictado no está disponible en este navegador. Usa el micrófono de tu teclado.');const r=new R();r.lang='es-BO';r.onresult=e=>{$('[name=q]').value=e.results[0][0].transcript};r.onerror=()=>notify('No se pudo captar voz. Revisa el permiso del micrófono.');r.start();notify('Escuchando…')}
 if(a==='simulate'){
 const data={scene:$('[name=labscene]').value,crop:$('[name=labcrop]').value,stage:$('[name=labstage]').value};
 const res=await api('simulate',data);
 $('#labresult').innerHTML=`<div class="eyebrow">Ensayo simulado · ${h(data.crop)}</div><h2 style="margin-top:12px">${h(data.scene)}</h2>${res.risks.map(x=>`<div class="alert"><b>${h(x.kind)} · ${x.date}</b><p>${h(x.evidence)}</p><small>${h(x.action)}</small></div>`).join('')||'<p>Ninguna regla se activó.</p>'}<small>Etapa: ${h(data.stage)} · Umbrales del piloto. Este ensayo no envía mensajes.</small>`;
 }
 if(a==='feedback'){const x=s.alerts.find(z=>z.id===Number(v));const pick=(key,label,val)=>`<label>${label}<select name="${key}" required><option value="">Selecciona</option><option value="1" ${val===1?'selected':''}>Sí</option><option value="0" ${val===0?'selected':''}>No</option></select></label>`;modal(`<h2>Observación de campo</h2><p>${h(x.kind)} · ${x.day} · ${h(x.ctx)}</p><form id="feedback" data-id="${x.id}" class="form">${pick('occurred','¿Ocurrió el fenómeno?',x.occurred)}${pick('useful','¿Fue útil la alerta?',x.useful)}<button>Guardar observación</button><div class="error"></div></form>`)}
 if(a==='doc'){const d=adm.docs.find(x=>x.id===Number(v))||{};modal(`<h2>${v?'Editar':'Nueva'} ficha</h2><form id="doc" class="form" data-id="${d.id||''}"><label>Título<input name="title" maxlength="80" required value="${h(d.title)}"></label>${field('crop','Cultivo',['Todos',...s.crops],d.crop)}<label>Palabras de consulta<input name="tags" required maxlength="200" value="${h(d.tags)}"></label><label>Orientación<textarea name="body" required maxlength="1200">${h(d.body)}</textarea></label><label>Fuente y versión<input name="source" required maxlength="200" value="${h(d.source)}"></label><button>Guardar ficha</button><div class="error"></div></form>`)}
 if(a==='case'){const x=adm.cases.find(x=>x.id===Number(v));await api('admin/case',{id:x.id,status:x.status==='Pendiente'?'Revisado':'Pendiente'});await team()}
 if(a==='logout'){adminKey='';adm=null;page='Monitor';await refresh()}
 if(a==='delete'&&confirm('¿Eliminar esta parcela y todo su historial?')){await api('delete',{});closeModal();await refresh()}
}
document.addEventListener('click',async e=>{const b=e.target.closest('[data-do]');if(!b)return;b.disabled=true;try{await action(b.dataset.do,b.dataset.arg)}catch(err){notify(err.message)}finally{b.disabled=false}});
document.addEventListener('submit',async e=>{
 if(e.target.hasAttribute('data-ops'))return; e.preventDefault();const f=e.target,data=formData(f),b=f.querySelector('button:not([type=button])');if(b.disabled)return;b.disabled=true;
 try{
 if(f.id==='channel'){const j=await api('channel',{text:data.text});const log=$('#channelLog');log.insertAdjacentHTML('beforeend',`<div class="bubble question">${h(data.text)}</div><div class="bubble">${h(j.reply)}</div>`);log.scrollTop=log.scrollHeight;f.reset();f.elements.text.value='';await refresh()}
 if(f.id==='offer'){await api('market',{...data,action:'offer'});closeModal();await refresh()}
 if(f.id==='chat'){await api('chat',{q:data.q});await refresh()}
 if(f.id==='profile'){data.consent=f.elements.consent.checked;await api('profile',data);closeModal();await refresh();notify('Parcela guardada')}
 if(f.id==='feedback'){await api('feedback',{id:Number(f.dataset.id),occurred:data.occurred==='1',useful:data.useful==='1'});closeModal();await refresh();notify('Observación guardada')}
 if(f.id==='login'){adminKey=data.key;try{await team()}catch(e){adminKey='';throw e}closeModal()}
 if(f.id==='doc'){await api('admin/doc',{...data,id:Number(f.dataset.id)||null});closeModal();await team()}
 if(f.classList.contains('plan')){await api('admin/plan',{number:Number(f.dataset.id),plan:data.plan});s=await api('state');await team();notify('Plan actualizado')}
 }catch(err){const el=f.querySelector('.error');if(el)el.textContent=err.message;else notify(err.message)}finally{b.disabled=false}
});
$('#team').onclick=()=>adminKey?team().catch(login):login();$('.close').onclick=closeModal;
refresh().then(()=>{if(location.hash==='#whatsapp')login()}).catch(e=>{$('#app').textContent='No se pudo abrir el cuaderno. '+e.message});
