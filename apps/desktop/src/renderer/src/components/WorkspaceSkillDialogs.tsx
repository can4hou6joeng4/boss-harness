import type { SkillReadResponse } from "@boss-harness/protocol";
import { CreateSkillDialog } from "./CreateSkillDialog";
import { DeleteSkillDialog } from "./DeleteSkillDialog";
import { EditSkillDialog } from "./EditSkillDialog";

/** 打开时固定目录与技能快照；工作区页面卸载不能销毁表单或在途操作。 */
export type WorkspaceSkillDialog =
  | { kind: "create"; root: string | null }
  | { kind: "edit" | "delete"; root: string | null; skill: SkillReadResponse };

interface Props {
  dialog: WorkspaceSkillDialog | null;
  onClose: () => void;
  /** 操作成功后由外层刷新全局目录，并保留返回技能页时可见的结果。 */
  onChanged: (notice: string) => void;
}

/** 与工作区导航独立挂载，通知切换背景会话时保留输入、确认、错误和提交锁。 */
export function WorkspaceSkillDialogs({ dialog, onClose, onChanged }: Props) {
  if (!dialog) return null;
  if (dialog.kind === "create") return <CreateSkillDialog root={dialog.root} onClose={onClose}
    onCreated={skill => onChanged(`已创建技能 ${skill.id}；目录刷新后可在列表中查看。`)} />;
  if (dialog.kind === "edit") return <EditSkillDialog skill={dialog.skill} root={dialog.root} onClose={onClose}
    onSaved={skill => onChanged(`已保存技能 ${skill.id}；技能目录与正文已刷新，下一回合生效。`)} />;
  return <DeleteSkillDialog skill={dialog.skill} root={dialog.root} onClose={onClose}
    onDeleted={id => onChanged(`已删除技能 ${id}；目录刷新后将从列表移除。`)} />;
}
