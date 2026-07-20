# 数据库升级说明

本项目不使用 Alembic。共享腾讯云 MySQL 的结构变更通过按编号排列的 SQL 文件管理。

## 规则

1. 已执行并提交的 SQL 文件不得修改。
2. 每次变更新建下一个编号，例如 `002_add_learning_record.sql`。
3. SQL 尽量使用 `IF NOT EXISTS`，避免重复执行造成破坏。
4. 执行前先查询 `schema_version`，确认脚本未执行。
5. 由一名数据库负责人在共享数据库执行，其他成员不要直接改表。
6. 执行成功后，脚本必须向 `schema_version` 写入自己的版本号。
7. 禁止在升级脚本中使用 `DROP DATABASE`、`TRUNCATE` 或无条件 `DELETE`。

## 查看当前版本

```sql
SELECT version, description, applied_at
FROM schema_version
ORDER BY version;
```

## 执行方式

可以在 Navicat 中打开 SQL 文件执行，也可以使用命令行：

```bash
mysql -h <host> -u <user> -p <database> < database/001_initial.sql
```

`Base.metadata.create_all()`继续负责首次创建 ORM 中不存在的表；SQL升级文件负责已经存在表的字段变更及后续业务表创建。
