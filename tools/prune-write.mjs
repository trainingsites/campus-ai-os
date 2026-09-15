/** Verified local replacement. No transport fallback to destructive in-place writes. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function contained(root, target) {
  const realRoot = fs.realpathSync(root);
  let ancestor = path.resolve(target);
  while (!fs.existsSync(ancestor)) {
    ancestor = path.dirname(ancestor);
  }
  const actual = fs.realpathSync(ancestor);
  return actual === realRoot || actual.startsWith(realRoot + path.sep);
}
export function applyPlan(root, plan) {
  const archive = path.resolve(root, plan.archive);
  let temp;
  try {
    if (!contained(root, plan.abs) || !contained(root, archive) || fs.lstatSync(plan.abs).isSymbolicLink()) throw Error('path outside campus or source symlink');
    if (!fs.readFileSync(plan.abs).equals(Buffer.from(plan.original))) throw Error('source changed since planning');
    fs.mkdirSync(path.dirname(archive), {recursive:true});
    if (!contained(root, archive) || (fs.existsSync(archive) && fs.lstatSync(archive).isSymbolicLink())) throw Error('archive symlink or escape');
    const fd = fs.openSync(archive, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_APPEND | fs.constants.O_NOFOLLOW, 0o600);
    try { fs.writeFileSync(fd, plan.archiveText); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    const preserved = fs.readFileSync(archive);
    for (const unit of plan.moved) if (!preserved.includes(Buffer.from(unit))) throw Error('archive verification failed');
    if (!fs.readFileSync(plan.abs).equals(Buffer.from(plan.original))) throw Error('source changed during archival');
    const mode = fs.statSync(plan.abs).mode & 0o777;
    temp = path.join(path.dirname(plan.abs), `.prune-${crypto.randomUUID()}.tmp`);
    const output = fs.openSync(temp, 'wx', mode);
    try { fs.writeFileSync(output, plan.replacement); fs.fsyncSync(output); } finally { fs.closeSync(output); }
    if (!fs.readFileSync(temp).equals(Buffer.from(plan.replacement))) throw Error('temporary replacement failed verification');
    if (!contained(root, plan.abs) || fs.lstatSync(plan.abs).isSymbolicLink() || !fs.readFileSync(plan.abs).equals(Buffer.from(plan.original))) throw Error('source changed before replacement');
    fs.renameSync(temp, plan.abs); temp = null;
    if (!fs.readFileSync(plan.abs).equals(Buffer.from(plan.replacement))) throw Error('replacement verification failed; archive retained');
    return {ok:true};
  } catch (e) { return {ok:false, code:'PRUNE_APPLY_FAILED', detail:e.message}; }
  finally { if (temp) { try { fs.unlinkSync(temp); } catch {} } }
}
