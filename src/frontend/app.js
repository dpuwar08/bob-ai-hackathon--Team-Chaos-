const API_BASE='https://bob-ai-hackathon-teamchaos.onrender.com/api';

let shipments=[],fleet=[],selectedShipmentId=null,temperatureChart,routeMap,scenarioTimer;

const elements={
  body:document.querySelector('#shipments-body'),
  chart:document.querySelector('#temperature-chart'),
  toast:document.querySelector('#toast'),
  recommendation:document.querySelector('#recommendation-content'),
  recommendationState:document.querySelector('#recommendation-state'),
  lastUpdated:document.querySelector('#last-updated'),
  feed:document.querySelector('#terminal-feed'),
  hours:document.querySelector('#simulation-hours'),
  hoursValue:document.querySelector('#hours-value'),
  delayCounter:document.querySelector('#delay-counter'),
  costCounter:document.querySelector('#cost-counter'),
  scenarioFill:document.querySelector('#scenario-meter-fill'),
  scenarioCopy:document.querySelector('#scenario-copy'),
  temperature:document.querySelector('#current-temperature')
};

async function api(path,options={}){
  const response=await fetch(`${API_BASE}/${path.replace(/^\//,'')}`,{
    headers:{'Content-Type':'application/json'},
    ...options
  });

  if(!response.ok){
    const detail=await response.json().catch(()=>({}));
    throw new Error(detail.detail||`REQUEST FAILED / ${response.status}`)
  }

  return response.json()
}

function showToast(message){
  elements.toast.textContent=message;
  elements.toast.classList.add('visible');
  clearTimeout(showToast.timeout);
  showToast.timeout=setTimeout(
    ()=>elements.toast.classList.remove('visible'),
    3500
  )
}

function riskClass(score){
  return score>=60?'high':score>=35?'medium':'low'
}

function formatStatus(value){
  return String(value||'unknown').replaceAll('_',' ')
}

function logDecision(message,type=''){
  const stamp=new Date().toLocaleTimeString([],{hour12:false});
  const line=document.createElement('div');
  line.className=`terminal-line ${type?`terminal-${type}`:''}`;
  line.innerHTML=`<span class="terminal-time">[${stamp}]</span> <span class="terminal-agent">AI/CORE</span> ${message}`;
  elements.feed.appendChild(line);

  while(elements.feed.children.length>5)
    elements.feed.firstChild.remove();

  elements.feed.scrollTop=elements.feed.scrollHeight
}

function renderMetrics(data){
  const riskCount=shipments.filter(s=>s.riskScore>=60).length;
  const reeferCount=fleet.filter(
    t=>t.status==='idle'&&t.refrigeration?.available
  ).length;
  const alerts=data.coldChainAlerts||[];

  document.querySelector('#shipment-count').textContent=shipments.length;
  document.querySelector('#risk-count').textContent=riskCount;
  document.querySelector('#reefer-count').textContent=reeferCount;
  document.querySelector('#cold-chain-status').textContent=alerts.length?'ALERT':'STABLE';
  document.querySelector('#cold-chain-note').textContent=
    alerts.length?`${alerts.length} THERMAL BREACH`:'ALL SENSORS NOMINAL';
  document.querySelector('#table-count').textContent=`${shipments.length} RECORDS`
}

function renderTable(){
  elements.body.innerHTML=shipments.map(s=>`
    <tr class="${s.id===selectedShipmentId?'selected':''}" data-shipment-id="${s.id}">
      <td>
        <span class="shipment-name">${s.reference}</span>
        <span class="shipment-id">${s.id}</span>
      </td>
      <td class="lane">${s.origin.split(' ')[0]} → ${s.destination.split(' ')[0]}</td>
      <td><span class="badge badge-status">${formatStatus(s.status)}</span></td>
      <td class="priority-${s.priority}">${s.priority}</td>
      <td><span class="badge badge-risk-${riskClass(s.riskScore)}">${s.riskScore} / 100</span></td>
    </tr>
  `).join('');

  elements.body.querySelectorAll('tr').forEach(row=>
    row.addEventListener('click',()=>{
      selectedShipmentId=row.dataset.shipmentId;
      renderTable();
      logDecision(`MANIFEST LOCK // ${selectedShipmentId} selected`)
    })
  )
}

function renderChart(){
  const cold=shipments.filter(s=>s.temperature);
  const labels=cold.map(s=>s.id.replace('SHP-2026-','SHP-'));
  const values=cold.map(s=>s.temperature.currentCelsius);

  if(values[0])
    elements.temperature.textContent=values[0].toFixed(1);

  if(temperatureChart)
    temperatureChart.destroy();

  temperatureChart=new Chart(elements.chart,{
    type:'line',
    data:{
      labels,
      datasets:[
        {
          label:'LIVE °C',
          data:values,
          borderColor:'#53e4f4',
          backgroundColor:'rgba(83,228,244,.1)',
          pointBackgroundColor:'#070d18',
          pointBorderColor:'#53e4f4',
          pointBorderWidth:2,
          pointRadius:4,
          tension:.35,
          fill:true
        },
        {
          label:'LIMIT 8°C',
          data:cold.map(s=>s.temperature.requiredMaxCelsius),
          borderColor:'#ff5d75',
          borderDash:[4,5],
          pointRadius:0,
          tension:0
        }
      ]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{
          callbacks:{
            label:c=>`${c.dataset.label}: ${c.parsed.y}°C`
          }
        }
      },
      scales:{
        x:{
          grid:{color:'rgba(83,228,244,.06)'},
          ticks:{
            color:'#58748a',
            font:{family:'Space Mono',size:8}
          }
        },
        y:{
          min:0,
          max:12,
          grid:{color:'rgba(83,228,244,.1)'},
          ticks:{
            color:'#58748a',
            font:{family:'Space Mono',size:8},
            callback:v=>`${v}°`
          }
        }
      }
    }
  })
}

function renderAlerts(alerts){
  document.querySelector('#cold-chain-alerts').innerHTML=
    alerts.length
      ?alerts.map(a=>
        `<span class="alert-item">⚠ ${a.reference}: ${a.currentCelsius}°C &gt; ${a.maximumAllowedCelsius}°C LIMIT</span>`
      ).join('')
      :'<span>NO ACTIVE THERMAL BREACHES</span>'
}

function initMap(){
  routeMap=L.map('route-map',{
    zoomControl:true,
    scrollWheelZoom:false
  }).setView([20.2,71.8],5.3);

  L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      attribution:'&copy; OpenStreetMap contributors',
      maxZoom:18
    }
  ).addTo(routeMap);

  const red='#ff5d75',
        lime='#b8f76b',
        cyan='#53e4f4',
        pune=[18.5204,73.8567],
        mumbai=[18.9497,72.9479],
        mundra=[22.8396,69.7219];

  L.polyline(
    [pune,mumbai],
    {
      color:red,
      weight:4,
      opacity:.95,
      dashArray:'10 9'
    }
  ).addTo(routeMap);

  L.polyline(
    [pune,[20.3,72.5],mundra],
    {
      color:lime,
      weight:4,
      opacity:.9
    }
  ).addTo(routeMap);

  [[pune,'PUNE HUB',cyan],
   [mumbai,'MUMBAI PORT / BLOCKED',red],
   [mundra,'MUNDRA GATEWAY / REROUTE',lime]
  ].forEach(([coords,label,color])=>{
    const icon=L.divIcon({
      className:'route-marker',
      html:`<span style="--marker:${color}"></span>`,
      iconSize:[16,16],
      iconAnchor:[8,8]
    });

    L.marker(coords,{icon})
      .addTo(routeMap)
      .bindTooltip(label,{direction:'top'})
  })
}

function renderRecommendation(result,whatIf=false){
  const route=
    result.routes?.find(
      r=>r.recommendation==='recommended'
    )||result.routes?.[0];

  const truck=result.idleTruckMatches?.[0];

  elements.recommendationState.textContent=
    whatIf?'SCENARIO MODELED':'ANALYSIS COMPLETE';

  elements.recommendation.innerHTML=`
    <p>
      ROUTE <strong>${route?.name||'PENDING'}</strong>
      is recommended for
      <strong>${result.shipment.reference}</strong>.
      ${
        whatIf
        ?`At ${result.scenario?.impact?.estimatedDelayHours||''}H disruption exposure, the route balances network delay, cost, and risk at a score of ${route?.evaluationScore??'—'}.`
        :`It provides the best combined delay, cost, and risk profile at a score of ${route?.evaluationScore??'—'}.`
      }
    </p>

    <div class="recommendation-detail">
      <span>ASSIGNED IDLE TRUCK</span>

      <strong>
        ${
          truck
          ?`${truck.truckId} · ${truck.driver}`
          :'NO COMPATIBLE UNIT'
        }
      </strong>

      <p>
        ${
          truck
          ?`${truck.refrigerated?'REFRIGERATED':'STANDARD'} UNIT // ${truck.location} // ${truck.capacityBufferKg.toLocaleString()} KG SPARE`
          :'Review fleet availability before dispatch.'
        }
      </p>
    </div>
  `;

  logDecision(
    `ROUTE SOLUTION // ${route?.name||'PENDING'} path scored ${route?.evaluationScore??'—'}`
  )
}

function updateScenarioPreview(){
  const hours=Number(elements.hours.value);

  elements.hoursValue.textContent=`${hours}H`;
  elements.delayCounter.textContent=hours;
  elements.costCounter.textContent=(18.5+hours*.39).toFixed(1);
  elements.scenarioFill.style.width=
    `${Math.max(4,Math.min(100,hours/1.68))}%`;

  elements.scenarioCopy.textContent=
    hours>48
      ?'Critical exposure: AI recommends immediate Mundra capacity reservation.'
      :hours>24
        ?'Elevated exposure: compare reroute capacity before dispatch.'
        :'Contained exposure: Mumbai lane remains viable with active monitoring.';

  clearTimeout(scenarioTimer);
  scenarioTimer=setTimeout(
    ()=>runWhatIf(true),
    420
  )
}

async function loadShipments(){
  const data=await api('shipments');

  shipments=data.shipments;
  fleet=data.fleet||[];

  selectedShipmentId||=shipments[0]?.id;

  renderMetrics(data);
  renderTable();
  renderChart();
  renderAlerts(data.coldChainAlerts||[]);

  elements.lastUpdated.textContent=
    `SYNC ${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`;

  logDecision(
    `MANIFEST SYNC // ${shipments.length} shipments indexed`
  )
}

async function optimize(){
  const result=await api('optimize',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      shipmentId:selectedShipmentId
    })
  });

  renderRecommendation(result);

  showToast(
    `OPTIMIZATION COMPLETE // ${selectedShipmentId}`
  )
}

async function triggerStrike(){
  await api('trigger-disruption',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      name:'Mumbai Port Strike',
      delayHours:24
    })
  });

  await loadShipments();

  logDecision(
    'DISRUPTION INJECTED // MUMBAI PORT STRIKE // RISK CASCADE UPDATED',
    'alert'
  );

  showToast('MUMBAI STRIKE APPLIED')
}

async function runWhatIf(silent=false){
  const hours=Number(elements.hours.value)||24;

  const result=await api('what-if',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      shipmentId:selectedShipmentId,
      disruptionName:'Mumbai Port Strike',
      delayHours:hours
    })
  });

  renderRecommendation(result,true);

  if(!silent)
    showToast(`${hours}H SCENARIO MODELED`)
}

async function safeAction(action){
  try{
    await action()
  }catch(error){
    logDecision(
      `API LINK ERROR // ${error.message}`,
      'alert'
    );

    showToast(error.message)
  }
}

document
  .querySelector('#simulation-hours')
  .addEventListener(
    'input',
    updateScenarioPreview
  );

document
  .querySelector('#what-if-button')
  .addEventListener(
    'click',
    ()=>safeAction(()=>runWhatIf())
  );

document
  .querySelector('#scenario-optimize')
  .addEventListener(
    'click',
    ()=>safeAction(optimize)
  );

document
  .querySelector('#trigger-button')
  .addEventListener(
    'click',
    ()=>safeAction(triggerStrike)
  );

document
  .querySelector('#optimize-button')
  .addEventListener(
    'click',
    ()=>safeAction(optimize)
  );

initMap();
updateScenarioPreview();
safeAction(loadShipments);