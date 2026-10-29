// Airtable-Automation → Aktion "Run a script"
// Input-Variable anlegen: recordId  =  Record ID des Triggers
let cfg = input.config();

const URL = "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/hooks/airtable";
const API_KEY = "REPLACE_WITH_CODEWORDS_API_KEY";
const HOOK_SECRET = "REPLACE_WITH_HOOK_SECRET";
const MODE = "preview"; // "apply" wenn der Lauf schreiben soll
const EVENT = "Airtable-Automation";

let res = await fetch(URL, {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${API_KEY}`
    },
    body: JSON.stringify({
        record_id: cfg.recordId,
        mode: MODE,
        event: EVENT,
        hook_secret: HOOK_SECRET
    })
});

let data = await res.json();
console.log(res.status, JSON.stringify(data));
output.set("status", res.status);
output.set("planned", data?.automation?.planned ?? 0);
