import test from 'node:test';
import assert from 'node:assert/strict';
import {typed,label,resolveConnections,commitConnections,validConnectionRecords,seedHistory} from './relationships.mjs';
const friend=typed('friend',false,1,2), enemy=typed('enemy',false,1,2), ally=typed('ally',false,1,2);
const seed=[{key:'legacy-1',event:1,value:friend,persist:true},{key:'legacy-1',event:8,value:enemy,persist:true}];
test('event-only deletion resumes continuing value and later base decisions win',()=>{
 const edits=[{key:'legacy-1',event:3,value:ally,persist:true},{key:'legacy-1',event:5,value:null,persist:false}];
 assert.equal(resolveConnections(seed,edits,5)['legacy-1'],undefined);
 assert.deepEqual(resolveConnections(seed,edits,6)['legacy-1'],ally);
 assert.deepEqual(resolveConnections(seed,edits,8)['legacy-1'],enemy);
});
test('continuing deletion stops at a later decision; custom same-event value wins',()=>{
 const edits=[{key:'legacy-1',event:3,value:null,persist:true}];
 assert.equal(resolveConnections(seed,edits,7)['legacy-1'],undefined);
 assert.deepEqual(resolveConnections(seed,edits,8)['legacy-1'],enemy);
 edits.push({key:'legacy-1',event:8,value:ally,persist:true});
 assert.deepEqual(resolveConnections(seed,edits,9)['legacy-1'],ally);
});
test('editing earlier does not overwrite later saved connection choice',()=>{
 const edits=[{key:'legacy-1',event:7,value:enemy,persist:true}];
 const next=commitConnections(edits,4,[{key:'legacy-1',field:'connection:legacy-1',value:ally}],new Set(['connection:legacy-1']));
 assert.deepEqual(resolveConnections([],next,6)['legacy-1'],ally);
 assert.deepEqual(resolveConnections([],next,7)['legacy-1'],enemy);
});
test('inverse selection reverses direction; mutual types display on both sides',()=>{
 const student=typed('mentor',true,1,2);
 assert.equal(label(student,1),'Student');assert.equal(label(student,2),'Mentor');
 assert.equal(student.source_id,2);assert.equal(label(friend,1),label(friend,2));
});
test('unchanged snapshots do not interrupt carry-forward; legacy duplicate pairs survive',()=>{
 const r={id:1,...friend},r2={id:2,...typed('mentor',false,1,2)};
 const data={events:[{id:1},{id:2}],relationships:{1:[r,r2],2:[r,r2]},characters:[{id:1},{id:2}]};
 const history=seedHistory(data);assert.equal(history.length,2);
 const edit={key:'legacy-1',event:1,value:enemy,persist:true};
 const resolved=resolveConnections(history,[edit],2);assert.equal(Object.keys(resolved).length,2);assert.deepEqual(resolved['legacy-1'],enemy);
 assert.deepEqual(validConnectionRecords([edit,{...edit,key:'legacy-99'},{...edit,value:{...enemy,target_id:9}}],data),[edit]);
});
