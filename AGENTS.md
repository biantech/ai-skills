# Global Instructions

## Communication

- 默认使用中文交流。
- Yuanchuan 项目的业务说明、Swagger `@Schema` 描述使用繁体中文。
- 日志、代码标识符和代码注释以英文为主。
- 不使用无必要的特殊字符或表情符号。

## Engineering

- 修改前先阅读相关实现、调用链和测试。
- 遵循现有架构和编码风格，不做无关重构。
- 先导入依赖，再使用依赖。
- 避免新增过时或未经验证的依赖。
- 保留用户已有的未提交修改。
- 未经要求不要创建分支、提交或推送代码。
- 修改后执行与改动范围匹配的验证。

## Yuanchuan Projects

The following rules apply only when the workspace is under
`/Users/bianjq/yuanchuan/`.

- 按照项目现有 DDD 分层架构开发。
- 不分析 `backup/` 目录下的文件。
- 新增字段和方法时添加简洁注释。
- 业务逻辑校验失败时使用
  `com.yuanchuan.common.exception.BusinessException`。
- String 判空优先使用
  `org.apache.commons.lang3.StringUtils`。
- List、Set、Map 判空优先使用
  `org.apache.commons.collections4.CollectionUtils`。
- 修改数据库字段时同步检查 PO、DTO、Mapper、XML、Repository 和相关测试。
- 新增数据库字段或表时，在模块 `guide/` 或 `sql/` 目录增加 SQL 文件。
- 新建表的主键使用 `int` 数据类型，不添加 `created_at`、`created_by` 字段。
- MyBatis-Plus 以 XML Mapper 为主要实现方式，尽量少用 Lambda 表达式。
- SQL 文件命名使用 `<table-name>_<YYYYMMDD>.sql`。
- 实施方案文件放到当前工作区的 `guide/plan/`。
- 查询或验证真实数据时必须使用全局 `db-tools` Skill。

## Yuanchuan Project Lookup
The following instructions apply only when the current workspace is under `/Users/bianjq/yuanchuan/`.
```text
ProjectHome=/Users/bianjq/yuanchuan

1. ${ProjectHome}/common → com.yuanchuan.common.*
2. ${ProjectHome}/activity → com.yuanchuan.activity.*
3. ${ProjectHome}/authentication → com.yuanchuan.authentication.*
4. ${ProjectHome}/file → com.yuanchuan.file.*
5. ${ProjectHome}/content → com.yuanchuan.content.*
6. ${ProjectHome}/finance → com.yuanchuan.finance.*
7. ${ProjectHome}/gateway-app → com.yuanchuan.gateway.*
8. ${ProjectHome}/location → com.yuanchuan.location.*
9. ${ProjectHome}/marketing → com.yuanchuan.marketing.*
10. ${ProjectHome}/merchant → com.yuanchuan.merchant.*
11. ${ProjectHome}/note → com.yuanchuan.note.*
12. ${ProjectHome}/order → com.yuanchuan.order.*
13. ${ProjectHome}/push → com.yuanchuan.push.*
14. ${ProjectHome}/ranking → com.yuanchuan.ranking.*
15. ${ProjectHome}/recommend → com.yuanchuan.recommend.*
16. ${ProjectHome}/reservation → com.yuanchuan.reservation.*
17. ${ProjectHome}/review → com.yuanchuan.review.*
18. ${ProjectHome}/search → com.yuanchuan.search.*
19. ${ProjectHome}/task → com.yuanchuan.task.*
20. ${ProjectHome}/user → com.yuanchuan.user.*

## Database Environments

For workspaces under `/Users/bianjq/yuanchuan/`:

- 未指定环境时使用 `local`。
- `local`、`devdb`、`db191` 均表示 local 环境。
- `dev001`、`dev236`、`db236`、`236` 均表示 dev001 环境。
- 不要把 `devdb` 误认为 `dev001`。
- 涉及真实记录、Mapper、Repository、数据库状态或 Schema 验证时，
  调用 `$db-tools`，不要根据代码猜测数据。
