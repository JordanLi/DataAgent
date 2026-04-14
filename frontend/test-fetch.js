const fetch = require('node-fetch');

async function test() {
  const res = await fetch('http://localhost:3000/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      conversation_id: null,
      datasource_id: 1,
      question: "test"
    })
  });
  console.log(res.status, res.statusText);
  console.log(await res.text());
}
test();
