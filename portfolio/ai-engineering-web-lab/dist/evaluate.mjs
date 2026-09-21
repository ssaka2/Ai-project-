export function evaluate({answer,required='',forbidden='',maxWords=80,jsonMode=false}) {
  if(typeof answer!=='string'||!answer.trim()||answer.length>20000) throw new Error('Enter a response between 1 and 20,000 characters.');
  if(typeof required!=='string'||typeof forbidden!=='string'||required.length>1000||forbidden.length>1000) throw new Error('Each term list must be at most 1,000 characters.');
  if(!Number.isInteger(maxWords)||maxWords<1||maxWords>10000) throw new Error('Maximum words must be a whole number from 1 to 10,000.');
  if(typeof jsonMode!=='boolean') throw new Error('JSON mode must be true or false.');
  const terms=s=>[...new Set(s.split(',').map(x=>x.trim().toLowerCase()).filter(Boolean))];
  const lower=answer.toLowerCase(), words=answer.trim().split(/\s+/u).length;
  const checks=[{name:`Word limit (${maxWords})`,passed:words<=maxWords,detail:`${words} words`}];
  for(const term of terms(required)) checks.push({name:`Required: ${term}`,passed:lower.includes(term),detail:'Text match'});
  for(const term of terms(forbidden)) checks.push({name:`Forbidden: ${term}`,passed:!lower.includes(term),detail:'Text match'});
  if(jsonMode){let valid=true;try{JSON.parse(answer)}catch{valid=false}checks.push({name:'Valid JSON syntax',passed:valid,detail:'Standard JSON parsing; no schema validation'});}
  return {passed:checks.filter(x=>x.passed).length,total:checks.length,words,checks};
}
