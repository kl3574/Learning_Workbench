M6.1 bounded independent UI review: two demonstrated blockers.

1. Shell.tsx:233 omits Authoring from the outer subject-lock dialog allow-list. Both unknown and independent Policy cases open the dialog but render only the generic policy message, so existing numeric Jobs cannot be discovered or cancelled. Actual Shell + actual AuthoringPanel/component HTTP fixtures: 2 RED.

2. useAuthoring.ts:114 checks current owner only before awaiting rejection-journal load. The old workspace read can settle after a new workspace is fully ready and then publish the old academic command body into that workspace. Actual hook + real DraftStore/fake-indexeddb: 1 RED. Check current owner/session and operation sequence after the await before updating projection.

No production file edited, no native or backend permission execution. Raw source snapshot and exact failing harness/log receipts are retained. The earlier Shell run failed solely because JSDOM lacks showModal and is classified as a harness error. Final source repair remains with the UI owner.
