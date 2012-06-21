ALTER TABLE interface DROP CONSTRAINT iface_master_fk;
ALTER TABLE interface DROP CONSTRAINT iface_vlan_parent_fk;

ALTER TABLE interface ADD CONSTRAINT iface_master_fk FOREIGN KEY (master_id) REFERENCES interface (id) ON DELETE CASCADE DEFERRABLE;
ALTER TABLE interface ADD CONSTRAINT iface_vlan_parent_fk FOREIGN KEY (parent_id) REFERENCES interface (id) ON DELETE CASCADE DEFERRABLE;

QUIT;
