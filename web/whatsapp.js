'use strict';
const $=q=>document.querySelector(q);
let current=null,version='',writing=false,polling=false;
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){const r=await fetch('/api/'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw Error(j.error||'Conexión interrumpida');return j}
function formatted(text){return escapeHtml(text).replace(/\*([^*\n]+)\*/g,'<strong>$1</strong>')}
function bubble(text,date,out=false){return '<div class="bubble '+(out?'mine':'')+'">'+(out?escapeHtml(text):formatted(text))+'<small>'+escapeHtml(date.slice(11,16))+'</small></div>'}
function render(d){
 const thread=$('#thread'),bottom=thread.scrollHeight-thread.scrollTop-thread.clientHeight<60;
 let items=d.mensajes.map(m=>({stamp:m.fecha,html:bubble(m.pregunta,m.fecha,true)+bubble(m.respuesta,m.fecha)}));
 for(const a of d.avisos){items.push({stamp:a.recibido,html:'<div class="bubble"><b>Alerta de prueba · '+escapeHtml(a.nivel)+'</b><br>'+escapeHtml(a.texto)+'<small>'+escapeHtml(a.recibido.slice(11,16))+'</small>'+(a.acuse?'<small>Recepción confirmada · '+escapeHtml(a.acuse.slice(11,16))+'</small>':'<button data-ack="'+a.id+'">Confirmar recepción</button>')+'</div>'})}
 items.sort((a,b)=>a.stamp.slice(0,19).localeCompare(b.stamp.slice(0,19)));let day='';
 thread.innerHTML='<div class="date">Conversación de prueba</div><div class="bubble"><b>Yapu IA</b><br>¡Hola! Registra tu cultivo para consultar el clima. También puedes generar un aviso desde el laboratorio y confirmarlo aquí.</div>'+items.map(e=>{const date=e.stamp.slice(0,10),label=day===date?'':'<div class="date">'+escapeHtml(date)+'</div>';day=date;return label+e.html}).join('');
 const prompts=d.alta?[['Ver pronóstico','¿Hay riesgo de helada mañana?'],['Consultar riego','¿Cómo reviso la humedad del suelo?']]:[['Registrar papa en Viacha','ALTA Viacha/Papa/Floración'],['Registrar quinua','ALTA Achacachi/Quinua/Emergencia']];
 $('#suggestions').innerHTML=prompts.map(([t,s])=>'<button data-text="'+escapeHtml(s)+'">'+escapeHtml(t)+'</button>').join('');
 $('#real').hidden=!d.numero;if(d.numero)$('#real').href='https://wa.me/'+d.numero;
 if(bottom||writing||!current)thread.scrollTop=thread.scrollHeight;
}
async function refresh(){if(polling)return;polling=true;try{const d=await api('productor/chat'),v=JSON.stringify(d);if(v!==version){render(d);current=d;version=v}if(!writing)$('#state').textContent='Conectado al simulador local'}catch(e){$('#state').textContent=e.message}finally{polling=false}}
async function send(text){if(writing||!text.trim())return;writing=true;$('#send').disabled=true;$('#state').textContent='Yapu está escribiendo…';try{await api('productor/chat',{text});$('#text').value='';await refresh();$('#state').textContent='Mensaje guardado'}catch(e){$('#state').textContent=e.message}finally{writing=false;$('#send').disabled=false}}
$('form').onsubmit=e=>{e.preventDefault();send($('#text').value)};
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.text){$('#text').value=b.dataset.text;$('#text').focus()}if(b.dataset.ack){b.disabled=true;try{await api('atlas/sim-ack',{id:Number(b.dataset.ack)});await refresh()}catch(err){$('#state').textContent=err.message;b.disabled=false}}});
refresh();setInterval(()=>{if(!document.hidden&&!writing)refresh()},2000);
