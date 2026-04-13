const echarts = require('echarts');
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body><div id="main" style="width: 600px;height:400px;"></div></body></html>');
const window = dom.window;
global.window = window;
global.document = window.document;
global.navigator = window.navigator;

const chart = echarts.init(document.getElementById('main'));

const option = {
  tooltip: { trigger: 'axis' },
  legend: { data: [ 'name', 'price', 'category' ] },
  grid: { containLabel: true, left: '5%', right: '5%', bottom: '5%', top: '15%' },
  xAxis: {
    type: 'category',
    data: [ '1', '2', '3' ],
    axisLabel: { rotate: 30 }
  },
  yAxis: { type: 'value' },
  series: [
    { name: 'name', type: 'bar', data: [ 0, 0, 0 ] },
    { name: 'price', type: 'bar', data: [ 999.99, 699.5, 150 ] },
    { name: 'category', type: 'bar', data: [ 0, 0, 0 ] }
  ]
};

chart.setOption(option);
console.log('Chart options successfully set');
