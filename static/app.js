const $=id=>document.getElementById(id);let ocrId=null;let chosenCandidate=null;let latestEstimate=null;
const today=new Date();$('period').value=`${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}`;
const notice=t=>$('notice').textContent=t;
async function api(path,data){const r=await fetch(path,data instanceof FormData?{method:'POST',body:data}:data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const j=await r.json();if(!r.ok)throw Error(j.error||'Request failed');return j;}
const safe=fn=>async e=>{try{await fn(e)}catch(err){notice(err.message)}};
function profile(){return Object.fromEntries(['disco','residential','arrangement','load_kw','phase','tariff_code','cycle_confirmed'].map(k=>[k,k==='cycle_confirmed'?$(k).checked:k==='residential'?($(k).value===''?null:$(k).value==='true'):$(k).value||null]));}
function history(){return $('history').value.split('\n').filter(x=>x.trim()).map(line=>{const p=line.split(',').map(x=>x.trim());if(p.length!==2)throw Error('History format: YYYY-MM, kWh');return {month:p[0],units:p[1]}})}
for(const b of document.querySelectorAll('nav button'))b.onclick=safe(async()=>{document.querySelectorAll('.tab').forEach(t=>t.hidden=t.id!==b.dataset.tab);document.querySelectorAll('nav button').forEach(t=>t.classList.toggle('active',t===b));notice('');if(b.dataset.tab==='saved'){const rows=await api('/api/bills');$('savedList').replaceChildren();if(!rows.length)$('savedList').textContent='No saved estimates yet.';for(const r of rows){const el=document.createElement('div');el.className='saved-row';const title=document.createElement('strong');title.textContent=`${r.input.period} · ${r.result.measured_units} kWh · ${r.result.status}`;const detail=document.createElement('details');const summary=document.createElement('summary');summary.textContent='View reading, tariff snapshot and OCR audit';const pre=document.createElement('pre');pre.textContent=JSON.stringify(r,null,2);detail.append(summary,pre);el.append(title,detail);$('savedList').append(el)}}});
$('photo').onchange=()=>{ocrId=null;chosenCandidate=null;$('source').value='manual';$('readingMode').textContent='Manual-reading fallback: type the current reading or extract it from the photo.';$('confirmed').checked=false;$('ocrReview').hidden=true};$('current').oninput=()=>{$('confirmed').checked=false};
$('scan').onclick=safe(async()=>{if(!$('photo').files[0])throw Error('Choose a meter photo first.');const f=new FormData();f.append('photo',$('photo').files[0]);f.append('precision',$('precision').value);const crop=['cropX','cropY','cropW','cropH'].map(k=>$(k).value);if(crop.some(Boolean)){if(!crop.every(Boolean))throw Error('Enter all four crop coordinates.');f.append('crop',JSON.stringify(crop.map(Number)))}$('scan').disabled=true;notice('Reading the photo…');try{const r=await api('/api/ocr',f);ocrId=r.id;$('source').value='ocr';$('readingMode').textContent='Photo reading: choose a candidate below, then verify or correct it.';$('confirmed').checked=false;$('ocrReview').hidden=false;$('cropPreview').src=r.crop_preview;$('ocrWarning').textContent=r.warning;$('raw').textContent=r.raw_text;$('candidates').replaceChildren();for(const c of r.candidates){const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent=`${c.raw_text} · confidence ${c.confidence}`;b.onclick=()=>{chosenCandidate=c.raw_text;$('current').value=c.value;$('confirmed').checked=false};$('candidates').append(b)}notice(r.candidates.length?'Inspect the crop and choose or correct the kWh reading.':'No readable candidates. Adjust the crop, upload a clearer photo or select manual fallback.')}finally{$('scan').disabled=false}});
$('saveProfile').onclick=safe(async()=>{await api('/api/profile',{profile:profile(),history:history()});notice('Consumer profile and history saved locally.')});
$('billForm').onsubmit=safe(async e=>{e.preventDefault();const data={reading:{previous:$('previous').value,current:$('current').value,confirmed:$('confirmed').checked,source:$('source').value,ocr_id:ocrId,chosen_candidate_raw:chosenCandidate,previous_date:$('previous_date').value,current_date:$('current_date').value,current_date_source:$('current_date').value?'user':'automatic'},period:$('period').value,profile:profile(),history:history()};if($('customEnabled').checked){if(!$('rate').value||!$('fixed').value)throw Error('Provide both custom amounts, including explicit zero where intended.');data.custom={rate:$('rate').value,fixed:$('fixed').value}}const r=await api('/api/calculate',data);renderEstimate(r);notice('Verified reading and estimate audit saved locally.')});
function addAppliance(){const row=document.createElement('div');row.className='appliance';for(const [key,label,value]of [['name','Appliance',''],['watts','Watts',''],['hours','Hours / day',''],['days','Days / month','30'],['quantity','Quantity','1']]){const l=document.createElement('label');l.textContent=label;const i=document.createElement('input');i.dataset.key=key;i.type=key==='name'?'text':'number';i.min='0';i.step='any';i.value=value;l.append(i);row.append(l)}const b=document.createElement('button');b.textContent='×';b.ariaLabel='Remove appliance';b.onclick=()=>row.remove();row.append(b);$('appliances').append(row)}$('addAppliance').onclick=addAppliance;addAppliance();
$('plan').onclick=safe(async()=>{const items=[...document.querySelectorAll('.appliance')].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(i=>[i.dataset.key,i.value])));const d={items};if($('planRate').value!==''){d.rate=$('planRate').value;d.fixed=$('planFixed').value;if($('budget').value!=='')d.budget=$('budget').value}const r=await api('/api/plan',d);$('planResult').replaceChildren();for(const text of [`Monthly appliance usage: ${r.monthly_kwh} kWh`,...r.items.map(i=>`${i.name||'Appliance'}: ${i.kwh} kWh`),r.estimated_cost===null?'Add a custom rate for cost estimates.':`Custom cost: PKR ${r.estimated_cost}`,r.budget_kwh===null?'':`Budget allowance: ${r.budget_kwh} kWh`,r.note]){const p=document.createElement('p');p.textContent=text;$('planResult').append(p)}if(r.budget_kwh!==null&&Number(r.monthly_kwh)>Number(r.budget_kwh)){const p=document.createElement('p');p.textContent=`Reduce planned consumption by at least ${(Number(r.monthly_kwh)-Number(r.budget_kwh)).toFixed(2)} kWh. Start by reducing hours on your highest-energy appliances.`;$('planResult').append(p)}});
api('/api/profile').then(d=>{if(d.profile)for(const[k,v]of Object.entries(d.profile)){if(!$(k))continue;if(k==='cycle_confirmed')$(k).checked=v===true;else $(k).value=v??''}if(d.history)$('history').value=d.history.map(r=>`${r.month}, ${r.units}`).join('\n')}).catch(e=>notice(e.message));

function renderEstimate(r){
 latestEstimate=r;
 if(r.calendar)renderCalendar(r.calendar);
 $('openLimit').hidden=!r.energy_estimate?.available;
 $('limitPanel').hidden=true;
 $('limitResult').replaceChildren();

 $('units').textContent=r.measured_units;
 $('explanation').replaceChildren();
 const paragraph=(text,parent=$('explanation'))=>{const p=document.createElement('p');p.textContent=text;parent.append(p)};
 const cash=v=>Number(v).toLocaleString('en-PK',{minimumFractionDigits:2,maximumFractionDigits:2});
 const est=r.energy_estimate;
 $('costTitle').textContent=est?'Base energy cost only':'Custom cost scenario';
 if(est?.available){
  $('total').textContent=est.minimum===est.maximum?`PKR ${cash(est.minimum)}`:`PKR ${cash(est.minimum)} – ${cash(est.maximum)}`;
  $('billStatus').textContent='February document scenario';
  $('costWarning').textContent='Base energy only — NOT the complete pre-tax bill. Fixed/minimum charges, surcharges and adjustments are also excluded, as are taxes and arrears.';
  for(const row of est.scenarios){const box=document.createElement('div');box.className='scenario';const strong=document.createElement('strong');strong.textContent=`${row.label}: PKR ${cash(row.energy_cost)}`;box.append(strong);paragraph(row.explanation,box);if(row.fixed_charge!==null)paragraph(`Additional fixed-charge scenario: PKR ${cash(row.fixed_charge)} (excluded above).`,box);$('explanation').append(box)}
  if(est.scenarios.length>1)paragraph('Your category is not known yet, so these are alternatives, not a claim that you qualify for the lowest rate.');
  paragraph('Assumptions: domestic Non-ToU meter below 5 kW; ordinary billing month; standard meter multiplier 1.');
  paragraph('Above 200 kWh, the ordinary-month scenario no longer uses protected rates. The February table charges 201–300 unprotected units at Rs. 33.10 each, without previous-slab benefit. Higher bands cost more. Eligibility still depends on the applicable history and billing-cycle rules.');
  paragraph(est.notice);
 }else{
  $('total').textContent=r.total===null?'PKR —':`PKR ${cash(r.total)}`;
  $('billStatus').textContent=r.status.replaceAll('_',' ');
  $('costWarning').textContent=est?.reason||'Your own flat-rate scenario, not an official LESCO bill.';
 }
 const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Calculation evidence & eligibility details';details.append(summary);paragraph(`Category: ${r.eligibility.category}; eligibility: ${r.eligibility.eligibility_status}`,details);for(const reason of r.eligibility.reason_codes)paragraph(reason.replaceAll('_',' '),details);if(est?.source)paragraph(est.source,details);$('explanation').append(details);
}

function renderCalendar(c){
 const pretty=d=>new Date(d+'T12:00:00').toLocaleDateString('en-PK',{day:'numeric',month:'short',year:'numeric'});
 $('todayLabel').textContent=pretty(c.today);$('issueLabel').textContent=pretty(c.next_issue_date);$('daysLabel').textContent=c.days_remaining===0?'Issued today':`${c.days_remaining} days`;
}
api('/api/dashboard').then(d=>{renderCalendar(d.calendar);$('period').value=d.calendar.today.slice(0,7);if(d.budget.target)$('billLimit').value=d.budget.target;if(d.budget.reserve!=null)$('chargeReserve').value=d.budget.reserve}).catch(e=>notice(e.message));
$('openLimit').onclick=()=>{$('limitPanel').hidden=false;$('limitPanel').scrollIntoView({behavior:'smooth',block:'center'});$('billLimit').focus()};
$('saveLimit').onclick=safe(async()=>{
 if(!latestEstimate?.energy_estimate?.available)throw Error('Calculate your meter usage first.');
 const r=await api('/api/budget',{target:$('billLimit').value,energy:latestEstimate.energy_estimate.maximum,reserve:$('chargeReserve').value||null,units:latestEstimate.measured_units,ac_watts:$('guideAcWatts').value,fridge_kwh:$('guideFridgeKwh').value});
 const texts=[r.basis,Number(r.over_by)>0?`Your entered usage is already Rs. ${r.over_by} over this planning target.`:`Room in your plan: Rs. ${r.remaining}`,r.daily_allowance===null?'Bill issuance is today. No remaining daily allowance is calculated.':`Illustrative allowance: Rs. ${r.daily_allowance} per day over ${r.days_remaining} days to issuance.`,r.reserve===null?'Other charges are unknown and not deducted. Set a reserve for a more cautious plan.':`Your chosen reserve: Rs. ${r.reserve}.`,'Where category is unknown, this uses the highest displayed energy scenario.',r.notice];
 $('limitResult').replaceChildren();
 if(r.guide?.available){
  const h=document.createElement('h3');h.textContent=`Daily appliance guide · ${r.guide.daily_kwh} kWh allowance`;$('limitResult').append(h);
  const ul=document.createElement('ul');ul.className='appliance-guide';for(const item of r.guide.items){const li=document.createElement('li');const strong=document.createElement('strong');strong.textContent=`${item.icon} ${item.title}`;const p=document.createElement('p');p.textContent=item.text;li.append(strong,p);ul.append(li)}$('limitResult').append(ul);
  texts.unshift(r.guide.warning,r.guide.basis);
 }else if(r.guide){texts.unshift(r.guide.reason)}
 for(const t of texts){const p=document.createElement('p');p.textContent=t;$('limitResult').append(p)}
});
