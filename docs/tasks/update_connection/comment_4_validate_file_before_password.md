# P2 - Validate the properties file before replacing the password

`src/sqlcl_conn_mng/cli.py` (PR #4 review, third round): for a combined password and metadata update on a properties file containing a comment or continuation line, the refusal in `update_properties` is not reached until after the password step has replaced the credentials.
