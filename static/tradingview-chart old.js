// tradingview-chart.js

// ตัวแปร global สำหรับการใช้งาน
let chart, candleSeries, ema5Series, ema20Series;
let volumeChart, volumeSeries, volumeMASeries;
let currentTimeframe = 'D';
let currentSymbol = 'PTT';
let data = [];
let volumeWithMA = [];
let ema5Data, ema20Data = [];
let emaVisible = true;
let currentMode = 'zoom';

// ฟังก์ชันเริ่มต้นกราฟ
function initializeCharts() {
    const container = document.getElementById('chart-container');
    const width = container.clientWidth;
    const height = Math.max(300, container.clientHeight * 0.7);

    // สร้างกราฟหลัก
    chart = LightweightCharts.createChart(document.getElementById("chart"), {
        width: width,
        height: height,
        layout: {
            background: { color: '#FFFFFF' },
            textColor: '#D9D9D9',
        },
        grid: {
            vertLines: { color: '#eee' },
            horzLines: { color: '#eee' },
        },
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#cccccc',
        },
        handleScroll: {
            mouseWheel: true,
            pressedMouseMove: true,
        },
        handleScale: {
            axisPressedMouseMove: true,
            mouseWheel: true,
            pinch: true,
        }
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: '#00C805',
        downColor: '#FF0000',
        borderUpColor: '#00C805',
        borderDownColor: '#FF0000',
        wickUpColor: '#003300',
        wickDownColor: '#660000',
        borderVisible: true,
        thinBars: false,
    });
    candleSeries.applyOptions({
        borderUpColor: '#00C805',
        borderDownColor: '#FF0000',
        borderVisible: true,
        borderWidth: 2,
    });

    // สร้างเส้น EMA
    ema5Series = chart.addLineSeries({
        color: '#00008B',
        lineWidth: 1,
        crosshairMarkerVisible: false,
        crosshairMarkerRadius: 4,
        crosshairMarkerBorderColor: '#1E90FF',
        crosshairMarkerBackgroundColor: '#FFFFFF',
        priceLineVisible: false,
        lastValueVisible: false
    });

    ema20Series = chart.addLineSeries({
        color: '#FF8C00',
        lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false,
        lastValueVisible: false
    });

    // สร้างกราฟปริมาณ
    volumeChart = LightweightCharts.createChart(document.getElementById('volume-chart'), {
        width: width,
        height: Math.max(100, container.clientHeight * 0.3),
        timeScale: {
            visible: false,
            borderVisible: false,
        },
        layout: { backgroundColor: '#fff', textColor: '#000', fontSize: 9 },
    });

    volumeSeries = volumeChart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        lastValueVisible: false,
        scaleMargins: { top: 0.1, bottom: 0 },
    });

    volumeMASeries = volumeChart.addLineSeries({
        color: '#FFA500',
        lineWidth: 1,
        title: '',
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        scaleMargins: { top: 0.1, bottom: 0 },
    });

    // ตั้งค่า time scale
    const commonTimeScaleOptions = {
        rightOffset: 0.5,
        barSpacing: 0.5,
        fixLeftEdge: false,
        fixRightEdge: false,
        lockVisibleTimeRangeOnResize: true,
        rightBarStaysOnScroll: true,
        borderVisible: true,
        borderColor: '#ccc',
        visible: true,
        timeVisible: true,
        secondsVisible: false
    };

    // สร้างกราฟสำหรับ Volume Profile
    const volumeProfileChart = LightweightCharts.createChart(
        document.getElementById('volume-profile-container'), 
        {
            width: 200,
            height: chart.height,
            layout: chart.options.layout,
            rightPriceScale: {
                visible: true,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
            leftPriceScale: {
                visible: false,
            },
            timeScale: {
                visible: false,
            },
            grid: {
                horzLines: {
                    visible: false,
                },
                vertLines: {
                    visible: false,
                },
            },
        }
    );

    const volumeProfileSeries = volumeProfileChart.addHistogramSeries({
        color: 'rgba(70, 130, 180, 0.7)',
        priceFormat: {
            type: 'volume',
        },
        priceScaleId: 'right',
    });

    chart.applyOptions({ timeScale: commonTimeScaleOptions });
    volumeChart.applyOptions({ timeScale: { ...commonTimeScaleOptions, visible: false } });

    // ซิงค์การเลื่อนระหว่างกราฟ
    syncScroll(chart, volumeChart);
    syncScroll(volumeChart, chart);

    // ตั้งค่า event listeners
    setupEventListeners();

}

function calculateVolumeProfile(data, priceBinSize = 1) {
    const volumeMap = new Map();

    data.forEach(bar => {
        const priceBin = Math.floor(bar.close / priceBinSize) * priceBinSize;
        const existingVolume = volumeMap.get(priceBin) || 0;
        volumeMap.set(priceBin, existingVolume + bar.volume);
    });

    const result = [];
    for (const [price, volume] of volumeMap.entries()) {
        result.push({ price, volume });
    }

    // เรียงลำดับตามราคา
    result.sort((a, b) => a.price - b.price);
    return result;
}

function updateVolumeProfile(data) {
    if (!data || data.length === 0) return;

    const profile = calculateVolumeProfile(data, 1); // กำหนดช่วงราคาเป็น 1 บาทต่อ bin

    const formattedData = profile.map(item => ({
        value: item.volume,
        price: item.price,
    }));

    volumeProfileSeries.setData(formattedData);
}

// ฟังก์ชันโหลดข้อมูล
function loadData(tf, from = null, to = null) {
    let url = `/tradingviewdata?symbol=${currentSymbol}&timeframe=${tf}`;
    if (from && to) {
        url += `&from=${from}&to=${to}`;
    }

    fetch(url)
        .then(res => res.json())
        .then(response => {
            currentTimeframe = tf;
            data = response;
            
            // แปลงข้อมูล EMA
            ema5Data = data.map(item => ({
                time: item.time,
                value: item.ema5
            }));
            
            ema20Data = data.map(item => ({
                time: item.time,
                value: item.ema20
            }));

            const volumeData = data.map(item => ({
                time: item.time,
                value: item.volume,
                color: item.close > item.open ? '#00FF00' : '#FF0000',
            }));

            volumeWithMA = calculateVolumeMA(data, 20);
            volumeMASeries.setData(volumeWithMA.map(item => ({
                time: item.time,
                value: item.volumeMA
            })));

            candleSeries.setData(data);
            volumeSeries.setData(volumeData);
            ema5Series.setData(ema5Data);
            ema20Series.setData(ema20Data);
            chart.timeScale().fitContent();
            volumeChart.timeScale().fitContent();

            // เชื่อม TimeScale ให้เลื่อนพร้อมกัน
            chart.timeScale().subscribeVisibleTimeRangeChange(timeRange => {
                volumeChart.timeScale().setVisibleRange(timeRange);
            });

            volumeChart.timeScale().subscribeVisibleTimeRangeChange(timeRange => {
                chart.timeScale().setVisibleRange(timeRange);
            });

            // อัปเดต Volume Profile
            updateVolumeProfile(data);

        });
}

// ฟังก์ชันคำนวณค่าเฉลี่ยปริมาณ
function calculateVolumeMA(data, period) {
    return data.map((item, index) => {
        if (index >= period - 1) {
            const sum = data
                .slice(index - period + 1, index + 1)
                .reduce((acc, val) => acc + val.volume, 0);
            return {
                ...item,
                volumeMA: sum / period
            };
        }
        return {
            ...item,
            volumeMA: null
        };
    }).filter(item => item.volumeMA !== null);
}

// ฟังก์ชันอัปเดตข้อมูลใน legend
function updateInfo(time) {
    const bar = data.find(d => d.time === time);
    const ema5 = ema5Data.find(d => d.time === time);
    const ema20 = ema20Data.find(d => d.time === time);
    const ma = volumeWithMA.find(d => d.time === time);
    if (!bar) return;
    document.getElementById('open-value').textContent = bar.open.toFixed(2);
    document.getElementById('high-value').textContent = bar.high.toFixed(2);
    document.getElementById('low-value').textContent = bar.low.toFixed(2);
    document.getElementById('close-value').textContent = bar.close.toFixed(2);
    document.getElementById('volume-value').textContent = bar.volume.toLocaleString();
    document.getElementById('volume-ma-value').textContent = ma ? ma.volumeMA.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '-';
    document.getElementById('ema5-value').textContent = ema5 ? ema5.value.toFixed(2) : '-';
    document.getElementById('ema20-value').textContent = ema20 ? ema20.value.toFixed(2) : '-';
}

// ฟังก์ชันซิงค์การเลื่อนระหว่างกราฟ
function syncScroll(masterChart, slaveChart) {
    let isSyncing = false;

    masterChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (isSyncing || range === null) return;
        isSyncing = true;
        slaveChart.timeScale().setVisibleLogicalRange(range);
        isSyncing = false;
    });
}

// ฟังก์ชันตั้งค่า event listeners
function setupEventListeners() {
    // Crosshair movement
    chart.subscribeCrosshairMove(param => {
        if (param.time && param.point) {
            updateInfo(param.time);
            volumeChart.setCrosshairPosition(param.point.x, 0);
        }
    });

    volumeChart.subscribeCrosshairMove(param => {
        if (param.time && param.point) {
            updateInfo(param.time);
            chart.setCrosshairPosition(param.point.x, 0);
        }
    });

    // Zoom/Pan mode
    document.getElementById("zoom-btn").addEventListener("click", () => setMode('zoom'));
    document.getElementById("pan-btn").addEventListener("click", () => setMode('pan'));

    // Theme controls
    document.getElementById('light-theme-btn').addEventListener('click', () => setTheme(false));
    document.getElementById('dark-theme-btn').addEventListener('click', () => setTheme(true));

    // Fullscreen
    document.getElementById('fullscreen-btn').addEventListener('click', toggleFullscreen);

    // Drag to zoom
    const chartDiv = document.getElementById("chart");
    const overlay = document.getElementById("drag-overlay");
    let isDragging = false;
    let dragStartX = 0;

    chartDiv.addEventListener("mousedown", (e) => {
        if (currentMode !== 'zoom') return;
        isDragging = true;
        dragStartX = e.offsetX;
        overlay.style.left = `${dragStartX}px`;
        overlay.style.width = `0px`;
        overlay.style.display = "block";
    });

    chartDiv.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const currentX = e.offsetX;
        const left = Math.min(dragStartX, currentX);
        const width = Math.abs(currentX - dragStartX);
        overlay.style.left = `${left}px`;
        overlay.style.width = `${width}px`;
    });

    chartDiv.addEventListener("mouseup", (e) => {
        if (!isDragging || currentMode !== 'zoom') return;
        isDragging = false;
        overlay.style.display = "none";

        const dragEndX = e.offsetX;
        if (Math.abs(dragEndX - dragStartX) < 10) return;

        const fromTime = chart.timeScale().coordinateToTime(Math.min(dragStartX, dragEndX));
        const toTime = chart.timeScale().coordinateToTime(Math.max(dragStartX, dragEndX));
        
        chart.timeScale().setVisibleRange({ from: fromTime, to: toTime });
    });

    // Window resize
    window.addEventListener('resize', () => {
        clearTimeout(window.resizeTimer);
        window.resizeTimer = setTimeout(resizeCharts, 200);
    });

    // Fullscreen change
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);
}

// ฟังก์ชันเปลี่ยนโหมด Zoom/Pan
function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.control-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`${mode}-btn`).classList.add('active');
    
    chart.applyOptions({
        handleScroll: {
            mouseWheel: true,
            pressedMouseMove: mode === 'pan',
        },
        handleScale: {
            axisPressedMouseMove: mode === 'zoom',
            mouseWheel: true,
            pinch: true,
        }
    });
}

// ฟังก์ชันรีเซ็ตกราฟ
function resetChart() {
    chart.timeScale().fitContent();
    volumeChart.timeScale().fitContent();
}

// ฟังก์ชันโหลดกราฟ
function loadChart() {
    currentSymbol = document.getElementById("symbol").value;
    updateTimeframeButtons();
    loadData(currentTimeframe);
}

// ฟังก์ชันเปลี่ยน timeframe
function changeTimeframe(tf) {
    currentTimeframe = tf;
    updateTimeframeButtons();
    
    if (isLargerToSmallerTimeframe(currentTimeframe, tf)) {
        const range = chart.timeScale().getVisibleRange();
        loadData(tf, range.from, range.to);
    } else {
        loadData(tf);
    }
}

// ตรวจสอบการเปลี่ยนจาก timeframe ใหญ่ไปเล็ก
function isLargerToSmallerTimeframe(oldTf, newTf) {
    const tfOrder = ['M', 'W', 'D', '15m'];
    return tfOrder.indexOf(oldTf) < tfOrder.indexOf(newTf);
}

// อัปเดตปุ่ม timeframe
function updateTimeframeButtons() {
    document.querySelectorAll('.timeframe-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase() === currentTimeframe.toLowerCase()) {
            btn.classList.add('active');
        }
    });
}

// ฟังก์ชันสลับแสดง/ซ่อน EMA
function toggleEMA() {
    emaVisible = !emaVisible;
    
    ema5Series.applyOptions({ visible: emaVisible });
    ema20Series.applyOptions({ visible: emaVisible });
    
    document.getElementById('toggle-ema-btn').textContent = emaVisible ? 'Hide' : 'Show';
    document.getElementById('ema-info').style.display = emaVisible ? 'flex' : 'none';
}

// ฟังก์ชันตั้งค่าธีม
function setTheme(isDark) {
    document.body.className = isDark ? 'dark-theme' : 'light-theme';
    
    const chartOptions = {
        layout: {
            background: { color: isDark ? '#121212' : '#FFFFFF' },
            textColor: isDark ? '#D9D9D9' : '#333333',
        },
        grid: {
            vertLines: { 
                color: isDark ? '#2B2B43' : '#EEEEEE',
                visible: true
            },
            horzLines: { 
                color: isDark ? '#2B2B43' : '#EEEEEE',
                visible: true
            }
        },
        crosshair: {
            vertLine: {
                color: isDark ? '#D9D9D9' : '#333333',
                labelBackgroundColor: isDark ? '#1E222D' : '#FFFFFF'
            },
            horzLine: {
                color: isDark ? '#D9D9D9' : '#333333',
                labelBackgroundColor: isDark ? '#1E222D' : '#FFFFFF'
            }
        },
        rightPriceScale: {
            borderColor: isDark ? '#2B2B43' : '#EEEEEE'
        },
        timeScale: {
            borderColor: isDark ? '#2B2B43' : '#EEEEEE'
        }
    };
    
    chart.applyOptions(chartOptions);
    volumeChart.applyOptions(chartOptions);
    
    ema5Series.applyOptions({
        color: isDark ? '#1E90FF' : '#2962FF',
        priceLineColor: isDark ? 'rgba(30, 144, 255, 0.3)' : 'rgba(41, 98, 255, 0.3)'
    });
    
    ema20Series.applyOptions({
        color: isDark ? '#FF8C00' : '#FF6D00',
        priceLineColor: isDark ? 'rgba(255, 140, 0, 0.3)' : 'rgba(255, 109, 0, 0.3)'
    });
    
    candleSeries.applyOptions({
        upColor: isDark ? '#00FF00' : '#089981',
        downColor: isDark ? '#FF0000' : '#f23645',
        borderUpColor: isDark ? '#00FF00' : '#089981',
        borderDownColor: isDark ? '#FF0000' : '#f23645',
        wickUpColor: isDark ? '#00FF00' : '#089981',
        wickDownColor: isDark ? '#FF0000' : '#f23645',
        borderVisible: true
    });

    const emaInfo = document.getElementById('ema-info');
    if (emaInfo) {
        const textColor = isDark ? '#FFFFFF' : '#000000';
        const yellowColor = isDark ? '#f2eb18' : '#ccaa00';

        emaInfo.querySelector('#open-value').parentElement.style.color = textColor;
        emaInfo.querySelector('#high-value').parentElement.style.color = textColor;
        emaInfo.querySelector('#low-value').parentElement.style.color = textColor;
        emaInfo.querySelector('#close-value').parentElement.style.color = textColor;

        emaInfo.querySelector('#volume-value').parentElement.style.color = yellowColor;
        emaInfo.querySelector('#volume-ma-value').parentElement.style.color = yellowColor;
    }

    document.getElementById('light-theme-btn').classList.toggle('active', !isDark);
    document.getElementById('dark-theme-btn').classList.toggle('active', isDark);
    
    localStorage.setItem('chartTheme', isDark ? 'dark' : 'light');
    
    chart.timeScale().fitContent();
    volumeChart.timeScale().fitContent();
}

// ฟังก์ชันจัดการ fullscreen
function toggleFullscreen() {
    const appWrapper = document.getElementById('app-wrapper');
    
    if (!document.fullscreenElement) {
        if (appWrapper.requestFullscreen) {
            appWrapper.requestFullscreen();
        } else if (appWrapper.webkitRequestFullscreen) {
            appWrapper.webkitRequestFullscreen();
        } else if (appWrapper.msRequestFullscreen) {
            appWrapper.msRequestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

function handleFullscreenChange() {
    resizeCharts();
    updateFullscreenButton();
}

function updateFullscreenButton() {
    const btn = document.getElementById('fullscreen-btn');
    if (!btn) return;
    
    btn.innerHTML = document.fullscreenElement 
        ? '<i class="fas fa-compress"></i> Exit Fullscreen' 
        : '<i class="fas fa-expand"></i> Fullscreen';
}

// ฟังก์ชันปรับขนาดกราฟ
function resizeCharts() {
    const container = document.getElementById('chart-container');
    if (!container) return;

    const width = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    const isFullscreen = !!document.fullscreenElement;
    
    const priceHeight = isFullscreen 
        ? Math.floor(containerHeight * 0.74)
        : Math.min(400, Math.floor(containerHeight * 0.7));
    
    const volumeHeight = isFullscreen
        ? Math.floor(containerHeight * 0.2)
        : Math.min(150, Math.floor(containerHeight * 0.3));
    
    chart.resize(width, priceHeight);
    volumeChart.resize(width, volumeHeight);
    
    adjustEMAControlsPosition();
}

function adjustEMAControlsPosition() {
    const emaControls = document.getElementById('ema-controls');
    if (!emaControls) return;
    
    if (document.fullscreenElement) {
        emaControls.style.top = '70px';
        emaControls.style.left = '20px';
    } else {
        emaControls.style.top = '50px';
        emaControls.style.left = '10px';
    }
}

// เริ่มต้นเมื่อโหลดหน้า
document.addEventListener('DOMContentLoaded', () => {
    // เริ่มต้นกราฟ
    initializeCharts();
    // อ่านค่าธีมจาก localStorage
    const savedTheme = localStorage.getItem('chartTheme') || 'light';
    setTheme(savedTheme === 'dark');

    
    // โหลดข้อมูลเริ่มต้น
    //loadChart();
    
    // ปรับขนาดกราฟหลังจากโหลด
    setTimeout(resizeCharts, 100);
});
