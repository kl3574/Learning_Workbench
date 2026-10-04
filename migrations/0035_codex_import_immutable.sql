-- Forward-only protection of the original 0033 source facts; no row rewrites.
CREATE TRIGGER codex_import_batches_update BEFORE UPDATE ON codex_import_batches BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_batches_delete BEFORE DELETE ON codex_import_batches BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_batches_replace BEFORE INSERT ON codex_import_batches WHEN EXISTS(SELECT 1 FROM codex_import_batches WHERE aggregate_job_id=NEW.aggregate_job_id) BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_previews_update BEFORE UPDATE ON codex_import_previews BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_previews_delete BEFORE DELETE ON codex_import_previews BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_previews_replace BEFORE INSERT ON codex_import_previews WHEN EXISTS(SELECT 1 FROM codex_import_previews WHERE import_id=NEW.import_id) BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_bindings_update BEFORE UPDATE ON codex_import_bindings BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_bindings_delete BEFORE DELETE ON codex_import_bindings BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
CREATE TRIGGER codex_import_bindings_replace BEFORE INSERT ON codex_import_bindings WHEN EXISTS(SELECT 1 FROM codex_import_bindings WHERE import_id=NEW.import_id OR source_id=NEW.source_id OR import_job_id=NEW.import_job_id OR aggregate_job_id=NEW.aggregate_job_id AND ordinal=NEW.ordinal) BEGIN SELECT RAISE(ABORT,'immutable Codex Import'); END;
