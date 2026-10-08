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

Three operations find a connection by name case-insensitively and act on the first match, which is the first connection directory in enumeration order. On NTFS that order is the case-insensitive order of the ids. Three of three observations agree `[diff]`:

- `rename -conn c1 c1r` with both `c1` (`ID01`, in `/dev/local`) and `C1` (`ID03`, at `/`) saved renamed **`C1`**, then replaced `ID01` with `ID03` in `/dev/local`. The output still said `Connection c1 has been renamed` (`ops/17_rename_conn`).
- `rename -conn x1 y1` with `x1` and `X1` saved renamed the right connection, because its id came first (`case/07_rename_lower`).
- `delete -folder /dev -force` with `C2` inside `/dev/local` and `c2` at `/` deleted the directory of **`c2`**, which is outside the folder, and left `C2` on disk at `/` (`ops/33_folder_delete_force`). The same command without a case collision deleted the right connection (`ops/50_folder_delete_force`).

`delete -conn X2` with `x2` and `X2` saved deleted `X2` (`case/13_delete_X2`), so plain `delete -conn` was not seen to pick the wrong one, but one sample does not rule it out. A SQLcl-free writer should resolve names case-sensitively by id, and should refuse, not reproduce, a lookup that is ambiguous.

### Atomicity

- No temporary, backup or lock file appeared in a connection directory or in `connection_folders/` during any capture `[diff]` (the 2 ms watcher found only the `sqlcl/aliases.xml.bak_<n>` files).
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

- `connmgr list` showed `pyid` under `f` and the other five at `/`; `connmgr show` printed all six with `Password: ******`; `connect -name pyid` and `connect -name badlast` each connected with the saved password, and `select user from dual` returned `PROBE` (`idrt/02_read`) `[round-trip]`.
- `rename -conn pyid pyid2`, `move -conn pyid2 /`, `clone -original pyid2 pyc` (the clone carried the password, 426 bytes) and `delete -conn pyid2` all worked on the Python-made id, and `delete -conn bad23` removed the 23-character directory (`idrt/03_rename` to `idrt/07_delete_bad23`) `[round-trip]`.
- SQLcl does not validate the directory name at all: any directory under `connections/` holding a `dbtools.properties` is a connection. The wallet does not depend on the directory it sits in, since a copied wallet worked under five different ids `[round-trip]`.
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
| Line ending | LF, also on Windows | `[diff]` `line_ending` is `LF` in every snapshot |
| Last line | ends with LF | `[diff]` `trailing_newline` is true in every snapshot |
| Encoding | UTF-8; non-ASCII characters are written as raw UTF-8 bytes, never as `\uXXXX` | `[diff]` `names/21_nonascii_cp1252`: `café1` stored as the bytes `C3 A9` for `é` |
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

**Blocked** for writing a wallet from pure Python. Producing a new wallet, or adding a password to one, would require reproducing the obfuscation that protects Oracle's auto-login wallet. Oracle does not document that format, so reproducing it means reverse-engineering Oracle's credential protection, and this investigation does not do that. No Python-written wallet was built or offered to SQLcl. The wallet operations that need no new wallet bytes do work from Python; see "What Works Without Writing a Wallet". A connection without a saved password needs no wallet file at all. A saved password works without a wallet only in plain text; see "Wallet-Free Alternatives".

### Observed Behaviour

These observations come from sizes, hash prefixes and SQLcl output only; no wallet byte was read or printed.

- Every connection directory holds a `credentials.sso`, with or without a saved password. A wallet without a password is 270 bytes and one with the dummy password is 426 bytes `[diff]` (`ops/01_save_pwd`, `ops/02_save_nopwd`).
- Each write produces new bytes. All 46 wallets SQLcl wrote in the `ops`, `case`, `imp`, `names`, `chars` and `fold` stores have distinct SHA-256 hashes, including the 43 without a password, and rewriting the same password with `-replace` changed the hash `[diff]` (`ops/06_save_replace_pwd`). A constant empty-wallet template therefore does not exist.
- SQLcl's credential code names these secret aliases: `dbtools.database.password.base64`, `dbtools.proxy.password.base64`, and the legacy `oracle.security.client.password`, `oracle.security.client.password1`, `oracle.security.client.username` and `oracle.security.client.connect_string`. `ConnectionCredentials` has a `cleanupLegacyPasswords` method `[javap]`. The wallet is opened through the `OraclePKI` provider (`Wallet`) and written through `oracle.security.pki.OracleWallet` `[javap]`.
- `show` reports `Password: ******` when a password is saved and `Password: not saved` otherwise `[output]`.
- `connect -save` without `-savepwd`, `clone -nopwd` and `clone -username` all write a 270-byte wallet with no password. A plain `clone` copies the password `[diff]` (`ops/02_save_nopwd`, `ops/39_clone_nopwd`, `ops/38_clone_user`, `ops/37_clone_plain`).

### What Works Without Writing a Wallet

- **Clone with password, rename, move, delete.** A wallet does not depend on the directory it sits in. A byte-for-byte copy of a SQLcl-written wallet worked under five other ids: `show` reported the password as saved, and `connect -name` connected with it `[round-trip]` (`idrt/02_read`). Rename, move and delete never touch the wallet `[diff]`.
- **A connection without a password.** A byte-for-byte copy of a SQLcl-written 270-byte wallet, placed beside a Python-written `dbtools.properties`, was shown as `Password: not saved` `[round-trip]` (`props/01_show`). Reusing a wallet that Oracle software generated as a template is a licence question for the follow-up, not a solution this investigation adopts.
- **Saving a new password into the wallet, and `show --check-password` without SQLcl,** stay open. The remaining route is Oracle's own published wallet library (Phase 7), which is not yet assessed.

### Wallet-Free Alternatives

These were tested in the store `nowallet`. Its connections are copies of `fold` connections, with the wallet removed or emptied, and with a Python-written `ojdbc.properties` for the last two rows. `<PW>` marks where SQLcl printed the dummy password; the capture replaced it.

| Connection directory holds | `connmgr list` / `show` | `connect -name` | Other operations |
| -------------------------- | ----------------------- | --------------- | ---------------- |
| `dbtools.properties` only, no `credentials.sso` | listed; `Password: not saved` | `ORA-01005: null password given; logon denied`, the same as for a SQLcl-written empty wallet (`nw_normal`) | `rename -conn`, `move -conn` work; `clone` writes a new 270-byte wallet for the clone |
| A 0-byte `credentials.sso` | listed; `Password: not saved`, but every load logs `SEVERE ... Wallet Version Not Supported` with a stack trace | `ORA-01005` | not tested further |
| No wallet, and `ojdbc.properties` with `password=<dummy>` | listed; `show` prints `Password: not saved` and then `password: <PW>`, so the password appears on the console in clear | connects; `select user from dual` returned `PROBE` | not tested |
| No wallet, and `ojdbc.properties` with `oracle.jdbc.password=<dummy>` | listed | connects; `select user from dual` returned `PROBE` | not tested |

Evidence: `nowallet/01_read`, `nowallet/02_ops` `[round-trip]` `[output]`. `ConnectionDefinition` names `ojdbc.properties`, `tnsnames.ora` and `connection.properties` beside `credentials.sso` as files of a connection directory `[javap]`.

Consequences for a SQLcl-free writer:

- **A connection without a saved password needs no wallet at all.** Writing only `dbtools.properties` gives a connection that SQLcl treats exactly like one it saved without `-savepwd`. Never write a 0-byte wallet.
- **A saved password is possible only in plain text,** through the JDBC connection-properties file `ojdbc.properties` in the connection directory. SQLcl reads it, but `show` reports `Password: not saved` and prints the value in clear, and the file is readable by anyone who can read the store. An auto-login wallet is documented by Oracle to open without any password, so it too protects the password mainly through file permissions; it does, however, keep the password off the console. Whether plain-text storage is acceptable is a decision for the follow-up task, not for this investigation.
