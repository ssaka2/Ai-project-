import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluate} from './dist/evaluate.mjs';
test('required terms and forbidden phrases are case insensitive',()=>{const r=evaluate({answer:'Run TESTS and keep rollback.',required:'tests, rollback',forbidden:'guaranteed'});assert.equal(r.passed,4);});
test('records missing and forbidden terms as failures',()=>{const r=evaluate({answer:'Guaranteed deployment',required:'tests',forbidden:'guaranteed'});assert.equal(r.passed,1);assert.equal(r.total,3);});
test('word limit is inclusive',()=>{assert.equal(evaluate({answer:'one two',maxWords:2}).passed,1);assert.equal(evaluate({answer:'one two',maxWords:1}).passed,0);});
test('JSON mode rejects malformed output',()=>{assert.equal(evaluate({answer:'{"ok":true}',jsonMode:true}).passed,2);assert.equal(evaluate({answer:'not json',jsonMode:true}).passed,1);});
test('invalid inputs reject instead of producing misleading scores',()=>{for(const input of [{answer:''},{answer:'ok',maxWords:0},{answer:'ok',maxWords:2.5},{answer:'x'.repeat(20001)},{answer:'ok',jsonMode:'true'}])assert.throws(()=>evaluate(input));});
test('duplicate and empty terms do not inflate results',()=>{assert.equal(evaluate({answer:'tests',required:'tests,TESTS, ,'}).total,2);});
