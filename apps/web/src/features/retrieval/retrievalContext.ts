import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import { contextTarget, type ReaderTarget } from '../reader/target'
/** Only a resolved Reader context can supply a default; parent expansion remains explicit. */
export function retrievalContext(context: ViewContext | null, course: ContentRef | null, resolved: boolean): ReaderTarget | null {
  return context && resolved && ['block', 'lesson'].includes(context.active_ref.entity)
    && ['lesson', 'worked_example'].includes(context.view_kind) ? contextTarget(context, course) : null
}
