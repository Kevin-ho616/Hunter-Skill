# 版权与许可：填写、写入、检查

用于第 4 节封装交付，适用于原创、开源衍生和混合路线。沿用项目的构建工具与隔离 FontTools 环境；权利资料、写入结果与检查证据须分别记录。工程可读不证明版权归属或授权已获确认。

## 1. 填写项目权利资料

在项目设计规则与授权记录中填写，复用已有确认，不为每次导出重复问相同问题。示例姓名、年份和许可不得直接当作已确认资料。

| 信息 | OpenType name ID | 填写规则 |
| --- | --- | --- |
| 版权声明 | 0 | 实际版权方与有依据的年份／年份范围；新作声明可用 `Copyright © [年份] [版权方].`，保留权利或开放授权的表述须与真实许可一致 |
| 制作方 | 8 | 实际公司／品牌／工作室；与设计者、版权方分开 |
| 设计者 | 9 | 实际设计者；继承字形作者与本次修改者分别说明 |
| 许可说明 | 13 | 实际许可证名称、许可文字或随包正式协议的明确引用，不凭空承诺商用、转授权或独占权 |
| 许可网址 | 14 | 已有、可访问且与本字体版本对应的授权页面；没有网址时注明不适用，不编造链接 |

字段可按语言记录不同文字；逐项列出平台、编码、语言与拟写内容。0 和 13 是正式交付核对的基本项；8／9／14 按项目真实资料填写或记录不适用理由。尚未确认的资料留在项目记录中标待确认，不能把 TODO、示例网址或别的项目版权人写进成品。审校仍可继续，正式分发状态与未定项分别报告。

衍生字体另保存：底字名称、官方来源、固定版本、原始文件 SHA-256、完整许可、原版权／NOTICE、保留字体名及修改分发条件。原始信息留作比对基线；保留原版权和许可，修改者署名追加说明，不把继承字形署为全部原创。OFL 底字遵守 OFL 的原版权／许可保留、衍生许可和保留字体名条件；其他底字按各自许可处理，不一律套 OFL。Skill 代码的 MIT 许可不自动适用于字体。

## 2. 在构建源写入

优先在项目的 FontBuilder／Glyphs／UFO 等源和已有导出代码中设置，保证再次构建仍保留。用 FontTools 修改已导出字体时，保留旧文件，输出到新版本目录；先写母文件，再派生网页字体。不得只改文件名、PDF 或 README。

以下是可嵌入现有构建脚本的最小写入方法。`updates` 的键为 `(nameID, platformID, encodingID, languageID)`，值为已确认文字；例如 `(0, 3, 1, 0x409)` 为 Windows Unicode 英文版权记录。中文及其他变体按实际语言分别填，不用一条英文记录冒充全部平台已更新。

```python
def write_name_records(font, updates):
    allowed = {0, 8, 9, 13, 14}
    for key, text in updates.items():
        if len(key) != 4 or key[0] not in allowed or not isinstance(text, str) or not text.strip():
            raise ValueError("Use confirmed, nonempty copyright / attribution / license records.")
    for (name_id, platform, encoding, language), text in updates.items():
        font["name"].setName(text, name_id, platform, encoding, language)
```

调用时用 `TTFont(source, recalcTimestamp=False)` 读取，传入项目记录的完整更新清单，保存到尚不存在的输出路径，再重新打开检查；不要覆盖原件。已有记录只更新同一键，其他语言记录不会自动同步。中文不能写入不支持该文字的旧编码；保存遇到编码错误时改正对应记录，不能静默丢字。

开源衍生时，name 0 的新内容保留对应原记录全文，再另起一行追加本次修改归属；name 13／14 保留原许可及链接，必要补充需与其兼容。原设计者和制作方的归属也按真实来源保留或补充。导出 CFF OTF 时另检查 `CFF ` Top DICT 已有的 Notice／Copyright：保留上游声明，必要时同步追加；不要为改版权重建字形或清空整张 name 表。跨轮廓格式转换时，确认这些归属信息仍在可读的 name 字段和许可文件中。

## 3. 逐文件回读检查

每个字重、每个交付的 TTF／OTF／WOFF／WOFF2 都重新打开，不只检查第一份或文件名。下面的示例核验实际 name 记录，`expected` 为项目已确认的最终记录，`base_records` 为从未修改底字读取的记录；原创项目不传底字。保留原声明允许追加文字，但不允许把原文删掉。

```python
def read_rights_records(font):
    return {(r.nameID, r.platformID, r.platEncID, r.langID): r.toUnicode()
            for r in font["name"].names if r.nameID in {0, 8, 9, 13, 14}}

def check_rights_records(font, expected, base_records=None):
    actual = read_rights_records(font)
    for name_id in (0, 13):
        if not any(key[0] == name_id and text.strip() for key, text in actual.items()):
            raise ValueError(f"Missing copyright / license record: name ID {name_id}")
    for key, text in expected.items():
        if actual.get(key) != text:
            raise ValueError(f"Metadata differs from approved text: {key}")
    for key, text in (base_records or {}).items():
        if key[0] in {0, 13, 14} and text.strip() and text not in actual.get(key, ""):
            raise ValueError(f"Upstream copyright / license record lost: {key}")
    return actual
```

使用示例时将实际记录保存为可回读的 JSON 列表，保留键的四个整数和完整文字，附字体路径、版本、哈希及 PASS／FAIL；未做项写 SKIP。该检查保留平台／语言键，转换器确需调整编码或记录结构时，先建立明确的原文迁移对照并逐项复核，不能仅因检查失败而删掉底字基线。

这段代码只核对指定的 name 记录，不自动检查权利身份、翻译含义、相互矛盾的许可文字或许可文件。仍须检查：

1. **各变体与 CFF**：遍历所有相关 name 记录，检查遗漏、乱码、空白和旧占位；与填写表逐条对应。回读 CFF 的 Notice／Copyright（如有），与原件和本次声明比较，不能把 name 表通过当成 CFF 已查。
2. **许可与归属文件**：随包保留原许可／NOTICE／版权文本及实际来源；有名称限制时核对新家族名／PostScript 名。核对嵌入的许可文字、链接、随包协议及 OS/2 嵌入设置一致。文件写入清单并记录哈希，解压后再次核对。
3. **元数据修改的影响**：比较修改前后轮廓、cmap、hmtx 及 GSUB／GPOS，确认没有误改；必要时用已有真实塑形与试排复核。跨 TTF／CFF 转换沿用工程参考的转换检查，不能要求不同轮廓格式的表字节相同。
4. **同版交付**：元数据变动也会改变字体字节。重建对应网页容器、刷新版本／哈希清单、重新验收并同步离线试排、技术字样册及其他含字体副本的文件；同轮廓且只是元数据变化时可沿用已记录的光学结论，但不能沿用旧文件哈希。

完成证据为已确认资料、实际写入清单、每份字体的回读值、底字原文保留对照、CFF／随包许可检查，以及当前版本清单。工具检查通过与人工权利确认分开记录；没有执行的安装／字体查看器显示验证也单独说明。

依据：[OpenType name 字段](https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids)、[FontTools setName](https://fonttools.readthedocs.io/en/latest/ttLib/tables/_n_a_m_e.html)、[OFL 正式条款](https://openfontlicense.org/open-font-license-official-text/)。
