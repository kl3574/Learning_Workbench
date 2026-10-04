import React from 'react'
import {createRoot} from 'react-dom/client'
import {CodexTurnEventsPanel} from '../src/features/codex/CodexTurnEventsPanel'
createRoot(document.getElementById('root')!).render(<CodexTurnEventsPanel workspace='workspace_event_native' turn='turn_native' run='job_native' admitted />)
