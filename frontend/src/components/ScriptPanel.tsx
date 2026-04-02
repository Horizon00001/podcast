interface ScriptPanelProps {
  scriptPath?: string
}

export function ScriptPanel({ scriptPath }: ScriptPanelProps) {
  return (
    <section>
      <h3>脚本预览</h3>
      <p>脚本文件路径：{scriptPath || '待生成'}</p>
      <p>后续可在此接入脚本同步高亮能力。</p>
    </section>
  )
}
