const gridEl = document.getElementById("grid");
let reporting = true;
let start = null, end = null;

function build(){
  gridEl.innerHTML = "";
  for(let y=0;y<10;y++){
    for(let x=0;x<10;x++){
      const d = document.createElement("div");
      d.className = "cell low";
      d.dataset.x = x;
      d.dataset.y = y;
      d.onclick = () => clickCell(x,y,d);
      gridEl.appendChild(d);
    }
  }
}

async function loadGrid(){
  const r = await fetch("/api/grid");
  const j = await r.json();
  const g = j.grid;
  for(let y=0;y<10;y++){
    for(let x=0;x<10;x++){
      const idx = y*10+x;
      const cell = gridEl.children[idx];
      const v = g[y][x];
      if(v>2) cell.className="cell high";
      else if(v>0.8) cell.className="cell mid";
      else cell.className="cell low";
      cell.textContent = v>0 ? Math.round(v*10)/10 : "";
    }
  }
}

function clickCell(x,y,el){
  if(reporting){
    const type = document.getElementById("typeSel").value;
    const sev = document.getElementById("sevSel").value;
    fetch("/api/reports",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({x,y,type,severity:sev})
    }).then(()=>loadGrid());
    return;
  }

  if(!start){
    start=[x,y];
    el.style.outline="3px solid blue";
  } else if(!end){
    end=[x,y];
    el.style.outline="3px solid green";
    requestRoute();
  } else {
    resetSel();
  }
}

async function requestRoute(){
  const r = await fetch(`/api/route?sx=${start[0]}&sy=${start[1]}&ex=${end[0]}&ey=${end[1]}`);
  const j = await r.json();
  if(j.path){
    highlight(j.path);
    document.getElementById("status").textContent = "Cost: "+Math.round(j.cost);
  } else {
    document.getElementById("status").textContent = "No path";
  }
}

function highlight(path){
  for(const c of gridEl.children){ c.style.outline="none"; }
  for(const [x,y] of path){
    const idx = y*10 + x;
    gridEl.children[idx].style.outline="2px dashed red";
  }
}

function resetSel(){
  start=null; end=null;
  for(const c of gridEl.children){ c.style.outline="none"; }
}

document.getElementById("modeBtn").onclick = () => {
  reporting = !reporting;
  document.getElementById("modeBtn").textContent = reporting ? "Tap grid to report" : "Select start/end";
};

document.getElementById("refresh").onclick = loadGrid;
document.getElementById("clear").onclick = () => {
  fetch("/api/clear",{method:"POST"}).then(()=>loadGrid());
};

build();
loadGrid();
