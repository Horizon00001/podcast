import type { RefObject } from 'react'

interface TerminalConsoleProps {
  currentTaskId: string | null
  terminalOutput: string
  logEndRef: RefObject<HTMLDivElement | null>
}

export function TerminalConsole({ currentTaskId, terminalOutput, logEndRef }: TerminalConsoleProps) {
  if (!terminalOutput) {
    return null
  }

  return (
    <div style={{
      marginTop: '16px',
      backgroundColor: '#0c0c0c',
      borderRadius: '8px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
      overflow: 'hidden',
    }}>
      <div style={{
        backgroundColor: '#333',
        padding: '8px 15px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ff5f56' }} />
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ffbd2e' }} />
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#27c93f' }} />
        <span style={{ color: '#aaa', fontSize: '12px', marginLeft: '10px', fontFamily: 'monospace' }}>
          Podcast Pipeline Console - {currentTaskId?.slice(0, 8)}
        </span>
      </div>

      <div style={{
        padding: '15px',
        height: '420px',
        overflowY: 'auto',
        fontFamily: '"Fira Code", "Source Code Pro", Consolas, Monaco, monospace',
        fontSize: '14px',
        lineHeight: '1.5',
        color: '#f0f0f0',
        backgroundColor: '#0c0c0c',
      }}>
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {terminalOutput}
        </pre>
        <div ref={logEndRef} />
      </div>
    </div>
  )
}
