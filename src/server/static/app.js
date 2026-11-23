// Poll the json endpoint of web_server.py and update the current value and the graph without reloading the page.
// Plain javascript only: the pi and the phones may have no internet, so nothing is loaded from outside.
'use strict';

// namespace identifier that createElementNS needs for svg elements, nothing is downloaded from it
const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';
const STATUS_LABELS = { normal: '정상', fault: '고장' };
const FLOW_DECIMAL_PLACES = 2;
const VIEW_UPDATE_INTERVAL_MS = 1000;

// drawing area inside the svg viewBox 0 0 360 200, the margins hold the axis labels
const GRAPH_SIZE = { width: 360, height: 200, left: 34, right: 10, top: 10, bottom: 24 };
const GRAPH_Y_TICK_STEP_LPM = 0.5;
const GRAPH_X_TICK_STEP_MS = 15 * 60 * 1000;
const GRAPH_FAULT_MARK_HEIGHT = 8;

const pageConfig = document.body.dataset;
const apiUrl = pageConfig.apiUrl;
const pollIntervalMs = Number(pageConfig.pollIntervalMs);
const graphMaxFlow = Number(pageConfig.graphMaxFlow);

let lastFlowData = null;  // body of the last successful response
let lastFetchedAtMs = 0;  // performance.now() of the last successful response
let isServerReachable = true;

function formatTwoDigits(number) {
  return String(number).padStart(2, '0');
}

// format a unix time as HH:MM in the timezone of the server, whatever timezone the phone uses
function formatServerClock(timeMs, utcOffsetMin) {
  const shiftedTime = new Date(timeMs + utcOffsetMin * 60 * 1000);

  return `${formatTwoDigits(shiftedTime.getUTCHours())}:${formatTwoDigits(shiftedTime.getUTCMinutes())}`;
}

function formatAge(ageS) {
  const wholeAgeS = Math.max(0, Math.floor(ageS));

  if (wholeAgeS < 60) {
    return `${wholeAgeS}초 전`;
  }
  if (wholeAgeS < 3600) {
    return `${Math.floor(wholeAgeS / 60)}분 ${wholeAgeS % 60}초 전`;
  }
  if (wholeAgeS < 86400) {
    return `${Math.floor(wholeAgeS / 3600)}시간 ${Math.floor((wholeAgeS % 3600) / 60)}분 전`;
  }

  return `${Math.floor(wholeAgeS / 86400)}일 전`;
}

function formatSignal(sample) {
  const rssiText = sample.rssi === null ? '--' : `${sample.rssi} dBm`;
  const snrText = sample.snr === null ? '--' : `${sample.snr} dB`;

  return `RSSI ${rssiText} / SNR ${snrText}`;
}

function setText(elementId, text) {
  document.getElementById(elementId).textContent = text;
}

function showStatusBadge(flowStatus) {
  const badge = document.getElementById('flow-status');
  badge.textContent = STATUS_LABELS[flowStatus] || flowStatus;
  badge.className = `badge badge-${flowStatus}`;
}

// the age keeps growing between polls, so it is extrapolated from the time of the last response
function getLatestAgeS() {
  const elapsedSinceFetchS = (performance.now() - lastFetchedAtMs) / 1000;

  return lastFlowData.latest.age_s + elapsedSinceFetchS;
}

function updateCurrentView() {
  document.getElementById('connection-message').hidden = isServerReachable;

  if (lastFlowData === null) {
    return;
  }

  const latest = lastFlowData.latest;
  const card = document.getElementById('current-card');
  const staleBadge = document.getElementById('stale-badge');

  if (latest === null) {
    setText('flow-value', '--');
    setText('flow-status', '데이터 없음');
    staleBadge.hidden = true;
    return;
  }

  const ageS = getLatestAgeS();
  const isStale = ageS > lastFlowData.stale_after_s;

  setText('flow-value', latest.flow_lpm === null ? '--' : latest.flow_lpm.toFixed(FLOW_DECIMAL_PLACES));
  showStatusBadge(latest.flow_status);
  staleBadge.hidden = !isStale;
  card.classList.toggle('is-stale', isStale);

  setText('received-time', latest.received_time_local);
  setText('received-age', formatAge(ageS));
  setText('device-name', latest.device_name || latest.dev_eui);
  setText('signal', formatSignal(latest));
}

function createSvgElement(tagName, attributes) {
  const element = document.createElementNS(SVG_NAMESPACE, tagName);
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, String(value));
  }

  return element;
}

function createGraphScale(flowData) {
  const plotWidth = GRAPH_SIZE.width - GRAPH_SIZE.left - GRAPH_SIZE.right;
  const plotHeight = GRAPH_SIZE.height - GRAPH_SIZE.top - GRAPH_SIZE.bottom;
  const plotBottom = GRAPH_SIZE.height - GRAPH_SIZE.bottom;
  const endTimeMs = flowData.server_time_ms;
  const startTimeMs = endTimeMs - flowData.history_window_s * 1000;

  return {
    startTimeMs: startTimeMs,
    endTimeMs: endTimeMs,
    plotBottom: plotBottom,
    getX: (timeMs) => GRAPH_SIZE.left + ((timeMs - startTimeMs) / (endTimeMs - startTimeMs)) * plotWidth,
    // values above the graph range are drawn on the top edge
    getY: (flowLpm) => plotBottom - (Math.min(Math.max(flowLpm, 0), graphMaxFlow) / graphMaxFlow) * plotHeight,
  };
}

function drawFlowAxis(svg, scale) {
  const plotRight = GRAPH_SIZE.width - GRAPH_SIZE.right;

  for (let flowLpm = 0; flowLpm <= graphMaxFlow + 1e-9; flowLpm += GRAPH_Y_TICK_STEP_LPM) {
    const y = scale.getY(flowLpm);
    svg.appendChild(createSvgElement('line', { x1: GRAPH_SIZE.left, x2: plotRight, y1: y, y2: y, class: 'grid-line' }));

    const label = createSvgElement('text', { x: GRAPH_SIZE.left - 4, y: y + 4, 'text-anchor': 'end', class: 'axis-label' });
    label.textContent = flowLpm.toFixed(1);
    svg.appendChild(label);
  }
}

// ticks fall on whole quarter hours of the server clock
function drawTimeAxis(svg, scale, utcOffsetMin) {
  const utcOffsetMs = utcOffsetMin * 60 * 1000;
  const firstTickMs = Math.ceil((scale.startTimeMs + utcOffsetMs) / GRAPH_X_TICK_STEP_MS) * GRAPH_X_TICK_STEP_MS
    - utcOffsetMs;

  for (let tickMs = firstTickMs; tickMs <= scale.endTimeMs; tickMs += GRAPH_X_TICK_STEP_MS) {
    const x = scale.getX(tickMs);
    svg.appendChild(createSvgElement('line', { x1: x, x2: x, y1: GRAPH_SIZE.top, y2: scale.plotBottom, class: 'grid-line' }));

    const label = createSvgElement('text', { x: x, y: GRAPH_SIZE.height - 6, 'text-anchor': 'middle', class: 'axis-label' });
    label.textContent = formatServerClock(tickMs, utcOffsetMin);
    svg.appendChild(label);
  }
}

// split the history into runs of normal samples, a fault or a gap longer than the stale limit ends a run
function splitIntoSegments(history, maxGapMs) {
  const segments = [];
  let currentSegment = [];
  let previousTimeMs = null;

  for (const point of history) {
    const isGap = previousTimeMs !== null && point.time_ms - previousTimeMs > maxGapMs;
    if ((point.flow_lpm === null || isGap) && currentSegment.length > 0) {
      segments.push(currentSegment);
      currentSegment = [];
    }
    if (point.flow_lpm !== null) {
      currentSegment.push(point);
    }
    previousTimeMs = point.time_ms;
  }
  if (currentSegment.length > 0) {
    segments.push(currentSegment);
  }

  return segments;
}

function drawFlowSegments(svg, scale, history, maxGapMs) {
  for (const segment of splitIntoSegments(history, maxGapMs)) {
    // a single sample has no line, so it is drawn as a dot
    if (segment.length === 1) {
      const point = segment[0];
      svg.appendChild(createSvgElement('circle', { cx: scale.getX(point.time_ms), cy: scale.getY(point.flow_lpm), r: 2.5, class: 'flow-point' }));
      continue;
    }

    const coordinates = [];
    for (const point of segment) {
      coordinates.push(`${scale.getX(point.time_ms).toFixed(1)},${scale.getY(point.flow_lpm).toFixed(1)}`);
    }
    svg.appendChild(createSvgElement('polyline', { points: coordinates.join(' '), class: 'flow-line' }));
  }
}

function drawFaultMarks(svg, scale, history) {
  for (const point of history) {
    if (point.flow_lpm !== null) {
      continue;
    }
    svg.appendChild(createSvgElement('rect', { x: scale.getX(point.time_ms) - 1.5, y: scale.plotBottom - GRAPH_FAULT_MARK_HEIGHT, width: 3, height: GRAPH_FAULT_MARK_HEIGHT, class: 'fault-mark' }));
  }
}

function drawGraph(flowData) {
  const svg = document.getElementById('flow-graph');
  svg.replaceChildren();

  const scale = createGraphScale(flowData);
  drawFlowAxis(svg, scale);
  drawTimeAxis(svg, scale, flowData.utc_offset_min);

  if (flowData.history.length === 0) {
    const label = createSvgElement('text', { x: GRAPH_SIZE.width / 2, y: GRAPH_SIZE.height / 2, 'text-anchor': 'middle', class: 'empty-label' });
    label.textContent = '이 기간에 받은 데이터가 없습니다';
    svg.appendChild(label);
    return;
  }

  drawFlowSegments(svg, scale, flowData.history, flowData.stale_after_s * 1000);
  drawFaultMarks(svg, scale, flowData.history);
}

// the next request is scheduled after the previous one ends, so slow responses never pile up
async function pollFlowData() {
  try {
    const response = await fetch(apiUrl, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    lastFlowData = await response.json();
    lastFetchedAtMs = performance.now();
    isServerReachable = true;
    drawGraph(lastFlowData);

  } catch (error) {
    isServerReachable = false;
    console.warn('flow data request failed', error);
  }

  updateCurrentView();
  setTimeout(pollFlowData, pollIntervalMs);
}

pollFlowData();
setInterval(updateCurrentView, VIEW_UPDATE_INTERVAL_MS);
