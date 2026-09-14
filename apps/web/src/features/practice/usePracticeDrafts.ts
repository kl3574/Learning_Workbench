import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { decodePracticeEnvelope, practiceDirty, practiceDraftStore, practiceKey } from './practiceDrafts'
export const usePracticeDrafts = createResponseDraftJournal({ store: practiceDraftStore, decode: decodePracticeEnvelope, dirty: practiceDirty, key: value => practiceKey(value.session_id) })
