INSERT INTO role (id, name, creation_date, comments)
	VALUES (role_id_seq.nextval, 'gatekeeper', SYSDATE,
		'role dedicated to authorization actions');

QUIT;
