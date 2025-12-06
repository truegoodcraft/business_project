BEGIN TRANSACTION;

-- Guard rail: manufacturing movements must never oversell
CREATE TRIGGER IF NOT EXISTS trg_item_movements_no_mfg_oversell_ins
BEFORE INSERT ON item_movements
WHEN NEW.source_kind = 'manufacturing' AND NEW.is_oversold = 1
BEGIN
    SELECT RAISE(FAIL, 'manufacturing movements cannot oversell');
END;

CREATE TRIGGER IF NOT EXISTS trg_item_movements_no_mfg_oversell_upd
BEFORE UPDATE ON item_movements
WHEN NEW.source_kind = 'manufacturing' AND NEW.is_oversold = 1
BEGIN
    SELECT RAISE(FAIL, 'manufacturing movements cannot oversell');
END;

COMMIT;
