# Findings: SQLcl 25.4.1 Saved-Connection Store Writes

Clean-room specification of what SQLcl writes to its saved-connection store, built from store diffs, `javap` signatures and constants, and round trips. No Oracle code, class file, `javap` dump or wallet byte is reproduced here (`open_questions.md`, Q1).

## Environment

| Item | Value |
| ---- | ----- |
| SQLcl | `Oracle SQLDeveloper Command-Line (SQLcl) version: 25.4.1.0 build: 25.4.1.022.0618` |
| JRE SQLcl runs on | Oracle JDK 17.0.15, the `JAVA_HOME` JDK (`show java`: `java.version= 17.0.15`, `file.encoding= UTF-8`) |
| OS | Windows 11 Enterprise 10.0.26200, Git Bash |
| Jars inspected | `dbtools-sqlcl.jar`, `dbtools-core.jar`, `dbtools-common.jar`, `oraclepki.jar` from `<sqlcl-dir>/lib` |
| Database | podman container `sqlcl-jar-probe-xe` (`gvenzl/oracle-xe:21-slim`), schema `PROBE`, connect string `//localhost:1537/XEPDB1` |
| Password | A random dummy password, held in a scratch file only and fed to SQLcl on stdin; never written here |

Every SQLcl run in this document uses the command line below, with the script on stdin. `<scratch-root>` is the session scratch directory; nothing under it is committed.

```bash
MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <scratch-root>/stores/<store> /nolog
```

## Evidence Tags

| Tag | Meaning |
| --- | ------- |
| `[diff]` | Observed in a store snapshot pair captured with `scripts/store_probe.py` |
| `[javap]` | Read from a class signature or a constant-pool string with `javap` |
| `[round-trip]` | A file written from Python was read back by SQLcl with the stated result |
| `[output]` | Exact SQLcl console output for the stated command |
| `[structure]` | Dummy-wallet structure and controlled metadata probes, without rendering secret content |
| `[standard]` | Linked public cryptographic specifications, original research or Oracle documentation |
| `[decompile]` | Read from decompiled code; used only if the Q1 escalation gate is passed |

## Side Effects of Any SQLcl Run

- The first SQLcl run with `-home <store>` creates `<store>/sqlcl/aliases.xml` (68 bytes) and an empty `<store>/sqlcl/history.log`, even with `-nohistory` and without touching a connection `[diff]` (`ops/01_save_pwd`).
- The next three runs each add one backup, `<store>/sqlcl/aliases.xml.bak_1` to `bak_3` (68 bytes each); later runs add none, so every long-used store ends with exactly three `[diff]` (`ops/02_save_nopwd`, `ops/03_save_dup`, `ops/04_save_dup_case`, `ops/05_save_replace_nopwd`).
- A SQLcl-free writer does not need to create any of these, and the read path already ignores them.

## Operation Effect Map

### Capture Method

Each capture ran one SQLcl script against a scratch store between two snapshots taken with `scripts/store_probe.py --command snapshot`, and was compared with `--command diff`. A thread listed the store every 2 ms while SQLcl ran, to catch temporary files that exist only during the write. Captures are cited as `<store>/<step>`; their snapshots are `<scratch-root>/snapshots/<store>__<step>__before.json` and `__after.json`. Connection ids are shown as stable labels (`ID01`, `ID02`, ...) because the ids themselves are random.

The stores, each started empty:

| Store | Content |
| ----- | ------- |
| `ops` | The main operation sequence, steps `01` to `53` |
| `case` | Connections whose names differ only in case |
| `imp` | `connmgr import` of a SQL Developer export |
| `names` | Name, folder and value validation, escaping and non-ASCII handling |
| `chars` | One saved connection per special character |
| `conc`, `conc2` | Concurrent writers |
| `idrt` | Phase 3: Python-generated and rule-breaking ids |
| `props` | Phase 4: Python-written `dbtools.properties` files and tolerance probes |
| `fold`, `foldrt`, `fprobe_<probe>` | Phase 5: a SQLcl-written tree, a Python-written tree, and `folders.json` tolerance probes |
| `nowallet` | Phase 6: connections without a wallet file, with a 0-byte wallet, and with `ojdbc.properties` |

`<CS>` below is `probe@//localhost:1537/XEPDB1`; `-password "<PW>"` stands for the dummy password, which was substituted only on stdin.

### Subcommand Inventory

`help connmgr` lists nine subcommands `[output]`, and `ConnectionStoreOptions` declares one command type for each of the same nine (`IMPORT_COMMAND`, `LIST_COMMAND`, `SHOW_COMMAND`, `TEST_COMMAND`, `CLONE_COMMAND`, `ADD_COMMAND`, `DELETE_COMMAND`, `MOVE_COMMAND`, `RENAME_COMMAND`) plus `OLD_COMMAND` for the legacy command name `[javap]`.

| Subcommand | Flags | Writes the store |
| ---------- | ----- | ---------------- |
| `import` | `-duplicates IGNORE\|RENAME\|REPLACE`, `-key`, `-strip-passwords`, `-oci` | yes |
| `list` | `-folder`, `-flat`, `-oci` | no |
| `show` | `-oci` | no |
| `test` | `-username` | no |
| `clone` | `-original`, `-username`, `-nopwd` | yes |
| `add` | `-folder` | yes |
| `delete` | `-conn`, `-folder`, `-force` | yes |
| `move` | `-conn`, `-folder` | yes |
| `rename` | `-conn`, `-folder` | yes |

`connect -save <name>` with `-savepwd` and `-replace` is the one writer outside `connmgr`.

### Effects per Operation

| Operation | Created | Changed | Deleted | Captures |
| --------- | ------- | ------- | ------- | -------- |
| `connect -save N -savepwd -password "<PW>" <CS>` | `connections/<new id>/dbtools.properties` with keys `name`, `type=ORACLE_DATABASE`, `connectionString`, `userName` in that order; `connections/<new id>/credentials.sso`, 426 bytes | none; `folders.json` untouched, so the connection is at `/` | none | `ops/01_save_pwd` `[diff]` |
| `connect -save N -password "<PW>" <CS>` (no `-savepwd`) | the same two files; `credentials.sso` is 270 bytes | none | none | `ops/02_save_nopwd` `[diff]` |
| `connect -save N -replace ...` over an existing `N` | none | `credentials.sso` only; the id and `dbtools.properties` are unchanged. Without `-savepwd` the saved password is dropped (426 to 270 bytes); with it the password is stored again (270 to 426) | none | `ops/05_save_replace_nopwd`, `ops/06_save_replace_pwd` `[diff]` |
| `connmgr add -folder /p/q` | `connection_folders/folders.json` when absent | `folders.json`: the folder and every missing parent are added | none | `ops/07_folder_add_top`, `ops/08_folder_add_nested`, `ops/09_folder_add_deep` `[diff]` |
| `connmgr move -conn N /p` | none | `folders.json` only: the id leaves its old folder list and is appended to the new one; moving to `/` removes it from every list | none | `ops/12_move_conn`, `ops/14_move_conn_again`, `ops/15_move_conn_root` `[diff]` |
| `connmgr rename -conn OLD NEW` | `connection_folders/folders.json` as `{"folders":[]}` when absent | `dbtools.properties` of the resolved connection, with `name` changed and the keys rewritten in reread order (see "Key Order"); the id is kept; the folder lists are unchanged when names do not collide in case | none | `case/07_rename_lower`, `ops/19_rename_conn_case`, `props/03_rename_extra` `[diff]` |
| `connmgr clone -original O NEW` | `connections/<new id>/` with `dbtools.properties` (keys in reread order) and `credentials.sso` holding the copied password (426 bytes) | none; the clone is placed at `/` even when `O` is in a folder | none | `ops/37_clone_plain`, `ops/41_clone_in_folder` `[diff]` |
| `connmgr clone -original O -username U NEW` | as above with `userName=U`; `credentials.sso` has no password (270 bytes) | none | none | `ops/38_clone_user` `[diff]` |
| `connmgr clone -original O -nopwd NEW` | as above with the original user; `credentials.sso` has no password (270 bytes) | none | none | `ops/39_clone_nopwd` `[diff]` |
| `connmgr delete -conn N` | none | `folders.json`, when the id was listed in a folder | `connections/<id>/` with both files | `ops/42_delete_conn`, `ops/44_delete_conn_in_folder` `[diff]` |
| `connmgr delete -folder /p` (empty) | none | `folders.json`: the folder is removed; removing the last folder leaves `{"folders":[]}`, and the file is kept | none | `ops/48_folder_delete_empty`, `ops/52_folder_delete_DEV` `[diff]` |
| `connmgr delete -folder /p -force` | none | `folders.json`: the whole subtree is removed | the directory of every connection in the subtree | `ops/50_folder_delete_force` `[diff]` |
| `connmgr rename -folder /p/q NEWNAME` | none | `folders.json` only; the second argument is a bare folder name, not a path | none | `ops/45_folder_rename` `[diff]` |
| `connmgr move -folder /a/b /dev` | none | `folders.json` only; the subtree moves with its connections | none | `ops/47_folder_move` `[diff]` |
| `connmgr import FILE` | `connections/<new id>/` per imported connection: `dbtools.properties` with keys `name`, `type=ORACLE_BASIC`, `host`, `port`, `serviceName`, `userName` in that order, and a 270-byte `credentials.sso` | none | none | `imp/01_import` `[diff]` |
| `connmgr import -duplicates RENAME FILE` | as above under the name `<name>_1` | none | none | `imp/03_import_dup_rename` `[diff]` |
| `connmgr import -duplicates REPLACE FILE` | a second connection directory with the same name; the existing one is not removed | none | none | `imp/04_import_dup_replace`, `imp/05_list` `[diff]` |

Only `connect -save` connects to the database before writing. `clone` with `-username other` succeeded although no user `OTHER` exists, so clone does not connect `[diff]` (`ops/38_clone_user`).

### Validation and Output

Success messages `[output]`:

| Operation | Success output |
| --------- | -------------- |
| `connect -save` | `Name: N`, `Connect String: CS`, `User: U`, `Password: ******` or `Password: not saved` |
| `add -folder` | `Folder /p has been added` (echoes the argument as given, for example `Folder rel has been added`) |
| `move -conn` | `Connection N has been moved to /p` |
| `rename -conn` | `Connection OLD has been renamed` |
| `clone` | `Connection NEW has been cloned` |
| `delete -conn` | `Connection N has been deleted` |
| `delete -folder` | `Folder /p has been deleted` |
| `rename -folder` | `Folder /p/q has been renamed` |
| `move -folder` | `Folder /a/b has been moved to /dev` |
| `import` | `Importing connection N: Success`, then `1 connection(s) processed` |

Failures; in every case below the connections and `folders.json` were left unchanged `[diff]`:

| Condition | Output `[output]` | Capture |
| --------- | ----------------- | ------- |
| `connect -save` with an existing name, same case, no `-replace` | `A connection named c1 already exists` | `ops/03_save_dup` |
| `rename -conn` or `clone` to an existing name, same case | `A connection named c2 already exists` | `ops/18_rename_conn_dup`, `ops/40_clone_dup` |
| Rename or delete of an unknown connection | `Could not find the specified connection: nosuch` | `ops/20_rename_missing`, `ops/27_delete_conn_missing` |
| Clone of an unknown connection | `Undefined connection c1r` | `ops/21_clone_plain` |
| Folder that does not exist | `Could not find the specified folder: /nope` | `ops/13_move_conn_missing_folder`, `ops/31_folder_delete_empty` |
| `add -folder` of an existing folder | `A folder named dev already exists in /` | `ops/10_folder_add_dup` |
| `rename -folder` to an existing sibling | `A folder named d already exists in a/b` | `ops/46_folder_rename_dup` |
| Invalid folder name | `Invalid folder name "pct%41x". Folder names can not be "..","." or containing a "/" or %[0-9-a-fA-F]{2}` | `names/11_folder_percent`, `names/12_folder_dot`, `ops/29_folder_rename` |
| `add -folder /` | `Performing / action is not allowed for root Folder` | `names/15_folder_root` |
| Non-empty folder without `-force` | `The folder you are trying to delete is not Empty. If you are sure, please retry the command with -force flag` | `ops/49_folder_delete_nonempty` |
| Invalid connection name | `a:b=c#d!e\f is not a valid connection name.` | `names/02_name_specials`, `names/05_name_slash` |
| `import` of an existing name with the default `IGNORE` | `Importing connection imp1: Failure - Duplicate connection` | `imp/02_import_dup_ignore` |

Validation rules:

- **Name uniqueness is case-sensitive.** `C1` is saved beside `c1` (`ops/04_save_dup_case`), `rename -conn c1r C2` succeeds beside `c2` (`ops/19_rename_conn_case`), and `/DEV` is added beside `/dev` (`ops/11_folder_add_dup_case`) `[diff]`.
- **Connection names** reject `/`, `#`, `\`, `'`, `?`, a backtick and a tab; `:`, `=`, `!`, `.`, `-`, `_`, `@`, `(`, `)`, `,`, `;`, `$`, `*`, `+`, `<`, `>`, `|`, `[`, `]`, `{`, `}`, `%`, `~`, `^`, inner spaces, a leading space and non-ASCII letters are accepted `[diff]` (`chars/01_specials`, `names/01_name_spaces`, `names/03_name_leading_space`, `names/21_nonascii_cp1252`). `&` could not be tested, because SQLcl's substitution variables consume it before the command runs.
- **Folder names** must not be `.` or `..`, and must not contain `/` or a `%` followed by two hex digits; the class constant is the regular expression `^(\.|\.\.|.*[/%].*|.*%[0-9a-fA-F]{2}.*)$` `[javap]` (`FolderUtils.INVALID_FOLDER_NAME_REGEX`), and the messages above match it `[output]`. A relative path (`rel`) is taken from the root, and a trailing `/` is ignored `[diff]` (`names/13_folder_no_slash`, `names/14_folder_trailing_slash`).
- **Input encoding.** SQLcl decodes its stdin with the Windows ANSI code page, not UTF-8: UTF-8 input `café` was stored as `cafÃ©`, while the same text sent as cp1252 was stored correctly. Its stdout is UTF-8 `[diff]` `[output]` (`names/10_folder_nonascii`, `names/21_nonascii_cp1252`).

### Case-Insensitive Lookup Defects

Two operations, `rename -conn` and `delete -folder -force`, find a connection by name case-insensitively and act on the first match, which is the first connection directory in enumeration order. On NTFS that order is the case-insensitive order of the ids. Three of three observations agree `[diff]`:

- `rename -conn c1 c1r` with both `c1` (`ID01`, in `/dev/local`) and `C1` (`ID03`, at `/`) saved renamed **`C1`**, then replaced `ID01` with `ID03` in `/dev/local`. The output still said `Connection c1 has been renamed` (`ops/17_rename_conn`).
- `rename -conn x1 y1` with `x1` and `X1` saved renamed the right connection, because its id came first (`case/07_rename_lower`).
- `delete -folder /dev -force` with `C2` inside `/dev/local` and `c2` at `/` deleted the directory of **`c2`**, which is outside the folder, and left `C2` on disk at `/` (`ops/33_folder_delete_force`). The same command without a case collision deleted the right connection (`ops/50_folder_delete_force`).

`delete -conn X2` with `x2` and `X2` saved deleted `X2` (`case/13_delete_X2`), so plain `delete -conn` was not seen to pick the wrong one, but one sample does not rule it out. A SQLcl-free writer should resolve names case-sensitively by id, and should refuse, not reproduce, a lookup that is ambiguous.

### Atomicity

- No temporary, backup or lock file appeared in a connection directory or in `connection_folders/` during any capture: the 2 ms watcher reported no transient file at all `[diff]`. The `sqlcl/aliases.xml.bak_<n>` files are persistent, not temporary.
- `folders.json` is read and rewritten in place with `Files.write`; the serializer also calls `Files.createDirectories` and `Files.createFile`, and no rename or lock call `[javap]` (`FolderSerializer` method references).
- Concurrent writers lose updates. Two processes each adding 10 folders kept all 20, but three processes each adding 60 kept 123 of 180, while all 180 commands printed `has been added` `[diff]` (`conc`, `conc2`). There is no locking, so a reader or a second writer can see or overwrite a stale tree.

## Connection Id

### Rule

A connection id is 16 bytes from `java.security.SecureRandom`, encoded with the URL-safe Base64 alphabet (`A-Z`, `a-z`, `0-9`, `-`, `_`) and no padding, which always gives 22 characters:

- `ConnectionIdentifiers$IdentifierGenerator` holds a static `SecureRandom` and a static `Base64.Encoder`. Its constant pool references `SecureRandom.nextBytes`, `Base64.getUrlEncoder`, `Encoder.withoutPadding` and `Encoder.encodeToString`, and nothing else that could derive the id from a name `[javap]`.
- All 20 ids SQLcl wrote during Phase 2 decode to exactly 16 bytes, re-encode to the same text, and end in one of `A`, `Q`, `g` or `w`, as the canonical encoding of 16 bytes requires. Both `-` and `_` occur `[diff]`.
- The ids are not UUIDs. The version nibble of byte 6 takes ten different values across the 20 ids, and the variant bits of byte 8 take all four values `[diff]`.

A Python equivalent is `base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode("ascii")`.

### Effect of Operations

| Operation | Id |
| --------- | -- |
| `rename -conn` | kept: the same directory's `dbtools.properties` is rewritten (`case/07_rename_lower`, `idrt/03_rename`) `[diff]` |
| `move -conn` | kept: only `folders.json` changes (`ops/12_move_conn`, `idrt/04_move`) `[diff]` |
| `connect -save -replace` | kept: only `credentials.sso` changes (`ops/05_save_replace_nopwd`) `[diff]` |
| `clone` | new random id for the clone; the original keeps its id (`ops/37_clone_plain`, `idrt/05_clone`) `[diff]` |
| `import -duplicates REPLACE` | new random id; the old connection is kept beside it (`imp/04_import_dup_replace`) `[diff]` |

### Id Round Trip

In the store `idrt`, SQLcl saved one connection, `seed`, with a password. A Python script then copied its directory byte for byte to five new directories and changed only the `name=` line of each `dbtools.properties`. It also wrote a `folders.json` listing the first copy in `/f`:

| Name | Directory name |
| ---- | -------------- |
| `pyid` | generated in Python by the rule above |
| `badlast` | 22 valid characters, but a last character (`B`) that no 16-byte encoding produces |
| `bad21` | 21 characters |
| `bad23` | 23 characters |
| `badplus` | 22 characters ending in `+`, outside the URL-safe alphabet |

Results:

- `connmgr list` showed `pyid` under `f` and the other five at `/`; `connmgr show` printed all five copies with `Password: ******`; `connect -name pyid` and `connect -name badlast` each connected with the saved password, and `select user from dual` returned `PROBE` (`idrt/02_read`) `[round-trip]`.
- `rename -conn pyid pyid2`, `move -conn pyid2 /`, `clone -original pyid2 pyc` (the clone carried the password, 426 bytes) and `delete -conn pyid2` all worked on the Python-made id, and `delete -conn bad23` removed the 23-character directory (`idrt/03_rename` to `idrt/07_delete_bad23`) `[round-trip]`.
- SQLcl does not validate the directory name at all: any directory under `connections/` holding a `dbtools.properties` is a connection. The wallet does not depend on the directory it sits in: the copied wallet was reported as saved under five ids, and connected under the two that were tried `[round-trip]`.
- `sqlcl-conn-mng list` showed only `badlast`, `pyc` and `seed` from that store, because `src/sqlcl_conn_mng/store.py:21` accepts only names of exactly 22 characters from the URL-safe alphabet. A store holding a directory SQLcl lists but the tool skips can only come from a writer other than SQLcl; this is recorded for the follow-up, and the tool is not changed here `[round-trip]`.

A SQLcl-free writer should generate ids by the rule above, which SQLcl accepts like its own.

## dbtools.properties

### Writer

- SQLcl writes the file with `java.util.Properties.store(Writer, String)`. `ConfigurationProperties` copies its entries with `new LinkedHashMap(Map)` and calls `ConfigurationProperties$OrderedProperties.store(Writer, String)`. The target is a `ConfigurationProperties$NoCommentsWriter`, which drops comment lines, over an `OutputStreamWriter` with an explicit charset `[javap]`.
- It reads the file with `Properties.load(Reader)` over an `InputStreamReader` with an explicit charset, then copies the entries into a `LinkedHashMap` `[javap]`.
- The JRE is the one in the environment table, Java 17.0.15.

### Format

| Property | Value | Evidence |
| -------- | ----- | -------- |
| Header | none: no comment line and no timestamp | `[diff]` every SQLcl-written file |
| Line | `key=value`, no spaces around `=` | `[diff]` |
| Line ending | LF, also on Windows | `[diff]` `line_ending` is `LF` for every SQLcl-written file |
| Last line | ends with LF | `[diff]` `trailing_newline` is true for every SQLcl-written file |
| Encoding | UTF-8; non-ASCII characters are written as raw UTF-8 bytes, never as `\uXXXX` | `[diff]` the SQLcl-written files for `café1` (`names/21_nonascii_cp1252`) and `über1` hold raw UTF-8, and a UTF-8 writer without `\u` escapes reproduces them byte for byte (see "Properties Round Trip") |
| Escaping in values | `\` as `\\`; `:` `=` `#` `!` with a leading `\`; a leading space as a backslash followed by the space; inner and trailing spaces unescaped; tab, newline, carriage return and form feed as `\t` `\n` `\r` `\f` | `[diff]` `names/03_name_leading_space` (`name=\ lead`), `names/06_cs_descriptor` (`\=` throughout the descriptor), `names/07_clone_user_specials` (`userName=u\:s\=e\#r\!\\x y`), `ops/01_save_pwd` (`//localhost\:1537/XEPDB1`); the control characters follow from `Properties.store` `[javap]`, since SQLcl's input cannot carry them |
| Escaping in keys | as in values, plus every space as a backslash followed by the space; the keys SQLcl writes contain none of these | `[javap]` |

### Key Set

| Written by | Keys |
| ---------- | ---- |
| `connect -save` | `name`, `type=ORACLE_DATABASE`, `connectionString`, `userName` `[diff]` (`ops/01_save_pwd`) |
| `connmgr clone` | the original's keys, with `name` and, given `-username`, `userName` replaced `[diff]` (`ops/38_clone_user`) |
| `connmgr import` of a basic SQL Developer connection | `name`, `type=ORACLE_BASIC`, `host`, `port`, `serviceName`, `userName` `[diff]` (`imp/01_import`) |
| `connmgr rename -conn` | the existing keys, with `name` replaced; unknown keys are kept `[diff]` (`props/03_rename_extra` kept `zzExtra`) |

`PropertyNames` also declares `url`, `proxyUserName`, `proxyDistinguishedName`, `databaseToolsConnectionId`, `ociAuthenticationMethod`, `ociProfile`, `ociRegion`, `ociTenancy` and the type values `ORACLE_BASIC`, `ORACLE_DATABASE`, `OCI_DBTOOLS` `[javap]`. No capture produced them; they come from import variants and OCI references, which are out of scope here.

### Key Order

- A newly created file keeps the order in which SQLcl builds it. `connect -save` writes `name, type, connectionString, userName`, and `import` writes `name, type, host, port, serviceName, userName` `[diff]`.
- A file SQLcl reads and writes back (rename, clone) gets the iteration order of the `Properties` object it was loaded into. On Java 17 that is a `ConcurrentHashMap` with a 16-slot table, so the keys come out by bucket index of their spread `String.hashCode`. For the four standard keys this happens to be alphabetical, `connectionString, name, type, userName`. For an imported connection it is `port, name, host, type, serviceName, userName`, not alphabetical. The Python prediction matched both observations `[diff]` (`ops/37_clone_plain`, `imp/06_rename_imported`).
- SQLcl does not depend on key order when reading. A Python file with the keys reversed was listed and shown normally `[round-trip]` (`props/01_show`, `tol_reorder`).

### Properties Round Trip

A Python prototype, kept in `<scratch-root>/poc/` and not committed, writes ordered key-value pairs with the escaping above, with no header, LF endings, a final LF and UTF-8.

- **Byte comparison.** The prototype parsed every `dbtools.properties` file in the scratch stores, kept each file's key order, and wrote it again. All 48 outputs were byte-identical to their inputs: 45 written by SQLcl and 3 Python-edited copies from the id round trip. The identical files include the leading-space name, the escaped descriptor connect string, the user name with `:`, `=`, `#`, `!` and `\`, and the non-ASCII values `[diff]`. There are therefore no differences to list.
- **SQLcl reads the Python files.** Each prototype file was placed in its own connection directory beside a SQLcl-written wallet, in the store `props`. `connmgr list` listed all nine files, and `connmgr show` printed the values that were written, field for field `[round-trip]` (`props/01_show`, `props/02_show_nonascii`):
  - `rt_plain`: the four standard keys.
  - `rt_specials`: the name `rt sp:e=c!` with one leading space, the descriptor connect string, and the user `u:s=e#r!\x y`.
  - `rt_nonascii`: the name `rt_café` and the user `über`.

### Properties Read Tolerance

Each probe below was written from Python and read by SQLcl; `connmgr show` printed the expected values for each `[round-trip]` (`props/01_show`, `props/02_show_nonascii`). Renaming a probe made SQLcl rewrite it in its own format (`props/03_rename_extra` to `props/06_rename_uesc`):

| Probe | SQLcl reads it | After a SQLcl rewrite |
| ----- | -------------- | --------------------- |
| `#` timestamp header line | yes | header dropped |
| Keys in reverse order | yes | not rewritten in this test |
| CRLF line endings | yes | LF |
| Unknown extra key `zzExtra` | yes | key and value kept |
| No final newline | yes | not rewritten in this test |
| Non-ASCII name written as `é` | yes, `show "tol_uésc"` found it | written back as raw UTF-8 |

A SQLcl-free writer can use the prototype's rules as is. Read tolerance means a stricter or looser reader on either side is harmless.

## folders.json

### Serializer

`FolderSerializer` (in `dbtools-common.jar`) builds a Jackson-jr `JSON` object with `JSON.builder()`, `enable` and `disable`. It serializes with `JSON.asString` and parses with `JSON.beanFrom`, reads with `Files.readString`, and writes with `Files.write(Path, byte[])`. Its path constants are `connection_folders` and `folders.json` `[javap]`.

### Schema

| Property | Value | Evidence |
| -------- | ----- | -------- |
| Location | `<store>/connection_folders/folders.json` | `[diff]` `ops/07_folder_add_top` |
| Top level | an object with the single key `folders`; the root folder has no object of its own | `[diff]` every capture |
| Folder object | keys `name`, `connections`, `folders`, always all three, in that order | `[diff]` |
| `connections` | connection ids; a moved or added id is appended at the end | `[diff]` `fold/02_moves`: `f2` moved before `f1` is listed first |
| `folders` | child folder objects, sorted by name in Java `String` order (UTF-16 code units: uppercase before lowercase, `A10` before `A2`), at every level | `[diff]` all 123 folders of `conc2`, and the `fold`, `names` and `conc` trees |
| Whitespace | none: compact JSON | `[diff]` |
| Final newline | none | `[diff]` `trailing_newline` is false in every snapshot |
| Encoding | UTF-8; non-ASCII written raw, `\` as `\\`, `<` and `>` unescaped | `[diff]` `names/21_nonascii_cp1252`, `fold/01_build`, `fold/02_moves` |
| No folders left | `{"folders":[]}`; the file is kept | `[diff]` `ops/52_folder_delete_DEV` |
| File absent | created by the first `add -folder` or `rename -conn`; not created by `connect -save`, `clone` or `import` | `[diff]` `ops/07_folder_add_top`, `props/03_rename_extra`, `ops/01_save_pwd`, `names/07_clone_user_specials`, `imp/01_import` |

### Folders Read Tolerance

Each probe was written from Python into a copy of the `fold` connections, then SQLcl ran `connmgr list` and `connmgr add -folder /zz`; the second command makes SQLcl rewrite the file (`fprobe_<probe>/01_list_add`) `[round-trip]`:

| Probe | `connmgr list` | File after the rewrite |
| ----- | -------------- | ---------------------- |
| A dangling id (no connection directory) in a folder | lists the raw id as if it were a connection name | dangling id kept |
| The same id in two folders | fails: `Duplicate connection found, please make sure the connection name is unique`; `add -folder` fails the same way | unchanged; every folder command fails until the file is fixed |
| Folder objects without `connections` or `folders` | works | the missing keys are added as `[]` |
| Unknown keys at the top level and in a folder | works | unknown keys dropped |
| Folders out of order | lists them sorted | rewritten sorted |
| A top-level `connections` list | ignored; the connection is at `/` because no folder lists it | key dropped |
| Indented JSON with CRLF and a final newline | works | rewritten compact, no newline |
| An empty file | works, no folders | rewritten as a normal document |
| Truncated, invalid JSON | fails with the Jackson parse error `Unexpected end-of-input within/between Object entries` | unchanged; `add -folder` fails the same way |

### Folders Round Trip

- **Byte comparison.** A Python prototype in `<scratch-root>/poc/`, not committed, renders a tree given as `{path: [ids]}` with siblings sorted by UTF-16 code units, compact separators, raw UTF-8 and no final newline. It was given the tree that SQLcl built in `fold/01_build` and `fold/02_moves`, which has seven folders, a `back\slash` name, a `lt<gt>` name, and two ids in move order. The output was byte-identical to SQLcl's file (465 bytes each) `[diff]`, so there are no differences to list.
- **SQLcl and the tool read the Python file.** The prototype wrote a different nested tree into the store `foldrt`: `/empty`, `/ops` holding `f3`, `/team/a/b` holding `f1`, and `/team/c` holding `f2`. `connmgr list` drew exactly that tree (`foldrt/01_list`). `sqlcl-conn-mng folders --format json` and `sqlcl-conn-mng list` reported the same folders and the same folder for each connection `[round-trip]`.

A SQLcl-free writer must never list one id in two folders. SQLcl does not repair such a file, and it refuses every folder command until the file is fixed.

## credentials.sso

### Verdict

**Accepted for SQLcl 25.4.1**: standard-library Python independently generated an empty wallet and two password-bearing wallets. SQLcl reported the expected password state and connected by each saved name; `select user from dual` returned `WALLET_PROBE` twice. The final writer read no Oracle wallet, template, extracted attribute or internal-password file. The previous blocker was superseded by the renewed Phase 6 experiments on 2026-10-08 `[round-trip]` (`fresh`, `accepted.txt`). This is feasibility evidence; the application still uses SQLcl for writes until the follow-up implementation.

### Method and Evidence

The analyser inspected only dummy wallets. Its output described structure, offsets, lengths, algorithm identifiers and fixed format discriminators; no credential, key, salt, IV, ciphertext or wallet dump was rendered. A new Python AES implementation passed the AES-128 and AES-256 published known-answer examples before wallet experiments. DER parsing, PBKDF2 and PKCS#12 MAC verification identified the wrapping and credential structure. No Oracle method body was decompiled or copied `[structure]` `[standard]`.

Public research supplied a candidate wrapper IV, which was independently confirmed by successful MAC verification on SQLcl-written wallets and the later SQLcl round trip. The candidate's source concerns Oracle 26ai; its other version/type claims are not assumed to describe SQLcl. References: [original wrapper research](https://www.0xchris.dev/posts/2026-08-31-deobfuscating-auto-login-wallets-in-oracle-26ai/), [PKCS#12 specification](https://www.rfc-editor.org/rfc/rfc7292), and [Oracle's AES256 wallet description](https://docs.oracle.com/en/database/oracle/oracle-database/21/dbseg/using-the-orapki-utility-to-manage-pki-elements.html) `[standard]` `[structure]`.

### Auto-Login Wrapper

The observed wrapper is 45 bytes; the DER PFX starts at offset 45. Integer fields are big-endian. These fixed format fields and independently generated random fields produced wallets accepted by SQLcl `[structure]` `[round-trip]`:

| Offset | Length | Meaning |
| ------ | ------ | ------- |
| 0 | 3 | File recognition marker, hexadecimal `A1 F8 4E` |
| 3 | 1 | Wallet type 55 (hexadecimal `37`) for the observed SQLcl format |
| 4 | 4 | Version 6 |
| 8 | 4 | Wrapped-key section length 33 |
| 12 | 1 | Scheme discriminator 6 |
| 13 | 16 | Newly generated random AES-128 wrapper key |
| 29 | 16 | One AES block containing the obfuscated internal PFX password |
| 45 | variable | DER-encoded PKCS#12 PFX |

Generate an independent 16-byte internal password with each byte in 1-127. XOR it with the fixed wrapper IV `c034d8311c02cef851f0144b81ed4bf2`, then AES-128-encrypt that single block with the newly generated wrapper key. No padding is used for this fixed-size block. Recovering it reverses those steps. This exact construction, including control characters in the internal password, passed the fresh-wallet tests `[structure]` `[round-trip]`. The internal password is unrelated to the database password.

### PKCS#12 Payload

The following construction was independently written from Python and accepted by SQLcl. Algorithm identities and parameter lengths also match the original dummy-wallet observations `[structure]` `[round-trip]`:

- PFX is a DER sequence of version 3, `authSafe` ContentInfo, and `MacData`.
- The outer ContentInfo has the `data` OID `1.2.840.113549.1.7.1`; its explicit context-0 value is an OCTET STRING containing the DER AuthenticatedSafe.
- AuthenticatedSafe is a sequence containing one `encryptedData` ContentInfo (OID `1.2.840.113549.1.7.6`). Its context-0 value is EncryptedData, version 0, containing EncryptedContentInfo with content type `data`.
- Encryption is PBES2 (`1.2.840.113549.1.5.13`), with PBKDF2 (`1.2.840.113549.1.5.12`): random 8-byte salt, 10,000 iterations, key length 32, PRF HMAC-SHA256 (`1.2.840.113549.2.9`, NULL parameters). PBKDF2's password input is the internal password's ASCII bytes.
- Its encryption scheme is AES-256-CBC (`2.16.840.1.101.3.4.1.42`) with a fresh random 16-byte IV. Apply PKCS#7 padding to the DER SafeContents and store ciphertext as the implicit context-0 primitive value (tag 128).
- MacData uses HMAC-SHA1, a fresh random 8-byte salt and 10,000 iterations. Its DigestInfo identifies SHA1 (`1.3.14.3.2.26`, NULL parameters), with a 20-byte digest.
- Derive the MAC key using PKCS#12 Appendix B, diversifier 3, SHA1 and length 20. Format the internal password as UTF-16BE characters with a two-byte zero terminator. Authenticate the complete DER AuthenticatedSafe bytes inside the outer OCTET STRING, rather than the PFX or wrapper `[standard]` `[round-trip]`.

### Empty and Password-Bearing SafeContents

An empty wallet encrypts an empty DER SEQUENCE as SafeContents. The fresh generated wallet was 270 bytes and SQLcl reported `Password: not saved` `[structure]` `[round-trip]`.

For a saved database password, SafeContents contains one SafeBag with bagId `1.2.840.113549.1.12.10.1.5` (`secretBag`). Its context-0 SecretBag is a SEQUENCE with secretTypeId `1.2.840.113549.1.16.12.12` and a context-0 value containing a SEQUENCE of two UTF8Strings: the alias `dbtools.database.password.base64`, then standard Base64 of the database password's UTF-8 bytes. Base64 is inside the encrypted payload; it is not the obfuscation mechanism `[structure]` `[round-trip]`.

The SafeBag also carries a SET of attributes containing `localKeyId` (`1.2.840.113549.1.9.21`), whose SET value contains a 24-byte OCTET STRING. The observed compatible structure is `[structure]` `[round-trip]`:

| Offset within localKeyId | Length | Value |
| ----------------------- | ------ | ----- |
| 0 | 4 | Fixed Oracle format discriminator, unsigned big-endian integer 3870708445 |
| 4 | 8 | Opaque; freshly randomized in the accepted writer |
| 12 | 4 | Entry-kind discriminator, unsigned big-endian integer 6 |
| 16 | 8 | Opaque; freshly randomized in the accepted writer |

A completely random 24-byte localKeyId made the password disappear from SQLcl's view. Controlled XOR mutations at every byte showed that changes at offsets 0-3 and 12-15 broke recognition, while all individually mutated opaque bytes remained readable. Keeping those two fixed discriminators and freshly randomizing both opaque regions fixed the failure. The final POC uses numeric format constants, with no attribute-template read `[structure]` `[round-trip]` (`attribute_probes`, `fresh`). The meaning of the opaque regions is not established.

### Fresh-Wallet Acceptance

The final writer generated three distinct wallets, with sizes 270, 426 and 426 bytes. SQLcl showed the empty password state, showed the saved state for both credential wallets, and completed two independent saved-name logins. Neither the dummy database password nor its Base64 representation occurred in clear in any generated wallet `[round-trip]` (`fresh`).

Seven further password values covered empty text, 2/16/30-character random ASCII values, quotes/backslash/punctuation, UTF-8 including a supplementary character, and 1,024-character ASCII. Independent Python reads recovered each exact value; SQLcl recognized all seven password aliases without wallet errors. Sizes were 391, 391, 409, 426, 426, 409 and 1,771 bytes `[round-trip]` (`edges`). Only the main 24-character dummy credential was tested against a live database. Alias presence does not establish whether a particular database accepts an empty, Unicode or long password.

SQLcl startup initially failed in Java's Windows Unix-domain temporary path. A process-local `JAVA_TOOL_OPTIONS=-Djdk.net.unixdomain.tmpdir=D:/temp/sqlcl-java-tmp` allowed the real round trips; SQLcl's launcher and installed files were unchanged. All calls used `-home` explicitly with a scratch store `[output]`.

### Security and Compatibility Boundary

This construction removes plaintext credentials from connection files and normal console output. The wrapper key resides in the auto-login file, so anyone who can read that file can recover its contents. Oracle explicitly states that file-system permissions provide auto-login-wallet security: [Oracle wallet security](https://docs.oracle.com/en/database/oracle/oracle-database/21/dbseg/using-the-orapki-utility-to-manage-pki-elements.html). Restrict access to the store and avoid secrets in command-line arguments and logs `[standard]` `[structure]`.

The POC proves the ordinary SQLcl 25.4.1 database-password wallet, not local auto-login wallets, TDE wallets, proxy credentials, certificates, old DES wallets, or other SQLcl versions. A production reader must validate lengths, algorithms, padding and MAC before exposing a presence result, reject unsupported formats, and never log the decoded secret. A production writer needs atomic replacement and explicit permissions. These are follow-up implementation requirements, not checks already satisfied by this scratch POC `[round-trip]` (scope of `fresh` and `edges`).

### Prior Wallet Observations and Alternatives

Original operation captures remain valid: SQLcl always wrote a wallet, its empty wallets were 270 bytes, password replacement changed its hash, and `clone -nopwd` or `clone -username` dropped the saved password. Rename, move and delete left its bytes untouched. Copying an existing wallet under another id connected successfully `[diff]` `[round-trip]` (`ops`, `idrt`).

The no-wallet metadata-only connection was readable and behaved like an empty wallet; a zero-byte wallet caused load errors. A plaintext `ojdbc.properties` password connected but was printed by `show`, so that alternative remains rejected. The earlier statement that plaintext was the only SQLcl-free way to save a password is superseded by `fresh` `[round-trip]` (`nowallet`, `fresh`).

## Runtime Comparison

The renewed wallet POC changes the recommendation: password saves are feasible in standard-library Python. Third-party runtime libraries and plaintext storage remain excluded. Java and SQLcl were acceptance readers, not dependencies of the final wallet writer `[round-trip]` (`fresh`, `edges`; `open_questions.md`, renewed outcome).

| | Pure Python | Python + JRE + `oraclepki` | Python + SQLcl |
| --- | --- | --- | --- |
| Dependencies | Python 3.13 standard library: existing metadata modules, `hashlib`, `hmac`, `secrets`, `base64`, plus independently implemented AES and DER | JRE and Maven artifact `com.oracle.database.security:oraclepki`; 23.8.0.25.04 is the previously costed example, not a latest-version assertion | SQLcl and a compatible Java runtime, as used today |
| Licences | Python runtime PSF; independently written repository code MIT; no copied third-party or Oracle implementation | Oracle Free Use Terms and Conditions for the jar; chosen JRE licence | SQLcl's Oracle Free Use Terms and Conditions; chosen JRE licence |
| Install footprint | No additional package or runtime; implementation size remains for the follow-up | Previously costed jar 506,013 bytes, plus JRE; local JDK 17.0.15 was 292 MB | Previously measured SQLcl 25.4.1 installation 108 MB, plus JRE |
| Windows, Linux, macOS | Windows POC accepted; byte-based algorithms require no native provider, but Linux/macOS execution and platform-specific permissions remain to be tested | Installed Oracle library read the generated wallets on Windows; other platforms were not tested here | Windows acceptance passed; other platforms were not tested here |
| Catalog coverage | All previously proved metadata operations; creation of empty/password wallets and reading the supported password alias now proved | Oracle library recognized generated password entries; standalone Maven create/update sequence remains outside the selected runtime | Existing commands and fresh Python-wallet acceptance |
| Remaining boundaries | Live connectivity still needs a driver or SQLcl; old/local/proxy/certificate wallet formats are not qualified; production corruption handling, permissions and atomic writes remain implementation work | Adds a prohibited third-party runtime library; no independent Maven installation was qualified | Requires the larger existing external installation |
| Allowed by current decisions | Yes | No, as a product runtime | Yes, as an optional existing compatibility/connectivity dependency |

The Python row's wallet coverage and Windows results are `[round-trip]` (`fresh`, `edges`); its dependency set is the independently written POC's imports `[structure]`. Oracle API coverage is backed by `OracleWallet.setWalletArray`, `getSecretStore` and `OracleSecretStore.containsAlias` signatures `[javap]` and actual reads of generated wallets `[round-trip]` (`attribute_probes`). Historical footprint figures are retained as earlier measurements, not new installation checks. The Maven example's metadata and licence are recorded in its [published POM](https://repo.maven.apache.org/maven2/com/oracle/database/security/oraclepki/23.8.0.25.04/oraclepki-23.8.0.25.04.pom) `[standard]`.

### Recommendation

Implement catalog writes and supported SQLcl 25.4.1 password wallets in pure Python, using the verified format above. Keep SQLcl optional for connectivity (`test` and the connect-before-save behavior) and unsupported-wallet compatibility. Saving a standard database password no longer inherently requires SQLcl `[round-trip]` (`fresh`).

Do not infer password presence from file size: the renewed probes produced password-bearing wallets from 391 to 1,771 bytes, and an empty-string secret is distinct from no password entry. Read and verify the supported wallet format instead `[round-trip]` (`edges`). Preserve existing unsupported wallets or fail clearly rather than overwriting unknown credential entries; test the production reader/writer's failure handling and permissions before shipping (follow-up requirement).

## Follow-Up

### Verdict per Command

These are feasibility verdicts for the follow-up implementation, not a claim that the current CLI has changed. The supported wallet is the ordinary SQLcl 25.4.1 database-password format proved above `[round-trip]` (`fresh`, `edges`).

| `sqlcl-conn-mng` command | Verdict | Evidence |
| ------------------------ | ------- | -------- |
| `list` | feasible without SQLcl, already implemented | Existing read path; id rule `[round-trip]` |
| `show` | feasible without SQLcl, already implemented | Existing read path `[round-trip]` |
| `show --check-password` | feasible without SQLcl for the supported wallet after validated parsing; missing wallet means no saved secret | Alias recognition and exact secret recovery `[round-trip]` (`fresh`, `edges`) |
| `folders` | feasible without SQLcl, already implemented | Python nested-folder round trip `[round-trip]` |
| `export` | feasible without SQLcl, already implemented | Existing metadata read path; properties/folders round trips `[round-trip]` |
| `add --no-save-password` | feasible without SQLcl; write properties and an empty wallet, or omit the wallet | Empty generated wallet and original no-wallet probe `[round-trip]` |
| `add` saving a password | feasible without SQLcl for the supported format | Two independently generated wallets logged in by saved name `[round-trip]` (`fresh`) |
| `add --replace` | feasible without SQLcl for the supported format; preserve id and atomically replace credentials; protect unknown entries | Independent writer `[round-trip]` and replace behavior `[diff]` (`ops/05_save_replace_nopwd`, `ops/06_save_replace_pwd`) |
| `add --replace --no-save-password` | feasible without SQLcl; replace password wallet with an empty wallet or remove it, retaining id | Empty writer `[round-trip]`; original replace effects `[diff]` |
| `delete` | feasible without SQLcl; remove the connection directory and folder references | Original operation captures `[diff]` |
| `rename` | feasible without SQLcl; update properties, preserve id/wallet | Properties round trip `[round-trip]`; operation effects `[diff]` |
| `move` | feasible without SQLcl; update folder references only | Folders round trip `[round-trip]`; operation effects `[diff]` |
| `clone` | feasible without SQLcl; new id, preserve wallet by copying, or generate empty wallet when dropping the password | Copied wallet login and generated empty wallet `[round-trip]`; clone effects `[diff]` |
| `add-folder` | feasible without SQLcl | Folders round trip `[round-trip]` |
| `delete-folder`, including `--force` | feasible without SQLcl | Original operation captures `[diff]` |
| `test` | still needs SQLcl or a database driver | Connectivity excluded by Q5; the wallet writer performs no database I/O |

### Implementation Rules

The metadata rules are backed by the original operation diffs and text-file round trips `[diff]` `[round-trip]`:

- Generate ids from 16 random bytes in URL-safe Base64 without padding.
- Write properties using the documented escaping/order, raw UTF-8, LF endings and final LF; use byte writes on Windows.
- Write compact folders JSON with all keys, siblings sorted by UTF-16 code units and ids in insertion order. Never assign one id twice.
- Apply case-sensitive uniqueness and the observed name rules. Reject ambiguous lookup.
- Replace files atomically and serialize this tool's writers; SQLcl itself does not share a writer lock.

The renewed wallet rules come from `fresh`, `edges`, and controlled attribute tests `[structure]` `[round-trip]`:

- Generate the supported wallet independently using the verified wrapper, encrypted SafeContents, localKeyId discriminators and MAC; never use a distributed Oracle wallet template.
- Generate new internal password, wrapper key, encryption/MAC salts, CBC IV and opaque localKeyId fields on each write.
- Keep the database password's Base64 only inside encryption. Never put a password in `ojdbc.properties`, properties output, logs, or process arguments.
- Determine presence by verified parsing and the exact database-password alias, not wallet size.
- Preserve or explicitly reject unsupported wallets and unrelated credential entries; do not silently replace them.

Production requirements: strict length/DER/algorithm checks, padding and MAC verification, atomic writes, secret-free error messages, restrictive POSIX permissions and Windows ACLs, and corrupted/unsupported-wallet tests. Those requirements still need implementation and acceptance; scratch compatibility tests do not certify them `[standard]` (Oracle auto-login permission guidance), `[round-trip]` (limits of this POC).

### Follow-Up Tasks

| Task | Scope |
| ---- | ----- |
| `sqlcl_free_catalog_writes` | Implement metadata catalog operations and the verified pure-Python wallet writer/reader. Cover empty/password saves, replacement, clone and password-presence checks; keep SQLcl optional for connectivity/unsupported formats. Add corruption, permission, atomicity and secret-output tests. Update README store-format/runtime descriptions and document any changed parameters |
| `store_id_directory_rule` | Decide whether to match SQLcl's tolerant directory enumeration instead of restricting reads to 22-character ids, based on the original id round trip |
| `sqlcl_stdin_encoding` | Correct the optional SQLcl adapter's Windows input/output encoding split, based on original non-ASCII probes |

Deferred qualification: Linux/macOS runs and permissions, other SQLcl versions, old/local/proxy/certificate wallets, remaining connection-property types, and connectivity through a separately selected driver. No follow-up product implementation was added by this investigation `[round-trip]` (Windows SQLcl 25.4.1 acceptance scope).
