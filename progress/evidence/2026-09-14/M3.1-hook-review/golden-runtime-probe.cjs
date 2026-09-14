const fs = require('node:fs'); const vm = require('node:vm');
const text=fs.readFileSync('apps/web/src/features/practice/usePracticeSession.test.tsx','utf8');
const start=text.indexOf('const frozenTarget:'); const end=text.indexOf('function session(');
const data=text.slice(start,end).replace('const frozenTarget: PracticeTarget','const frozenTarget').replace('const questions: QuestionPublic[]','const questions');
process.stdout.write(vm.runInNewContext(data+'JSON.stringify({frozenTarget,questions,questionHashes})'));
