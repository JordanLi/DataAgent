const columns = ['id', 'name', 'price'];
const rows = [{ id: 1, name: 'Laptop', price: 999.99 }, { id: 2, name: 'Phone', price: 699.5 }, { id: 3, name: 'Desk', price: 150 }];
const chart_type = 'bar';

const xAxisCol = columns.find(c => typeof rows[0]?.[c] === 'string' || isNaN(Number(rows[0]?.[c]))) || columns[0]

const yAxisCols = columns.filter(c => {
  if (c === xAxisCol) return false
  const val = rows[0]?.[c]
  return val !== null && val !== undefined && !isNaN(Number(val))
})

console.log('xAxisCol:', xAxisCol);
console.log('yAxisCols:', yAxisCols);

const series = yAxisCols.map(col => ({
  name: col,
  type: chart_type,
  data: rows.map(r => Number(r[col]) || 0)
}))

console.log('series:', JSON.stringify(series, null, 2));

const option = {
  tooltip: { trigger: 'axis' },
  legend: { data: yAxisCols },
  grid: { containLabel: true, left: '5%', right: '5%', bottom: '5%', top: '15%' },
  xAxis: {
    type: 'category',
    data: rows.map(r => String(r[xAxisCol])),
    axisLabel: { rotate: 30 }
  },
  yAxis: { type: 'value' },
  series
}
console.log('option:', JSON.stringify(option, null, 2));
