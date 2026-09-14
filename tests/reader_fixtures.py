"""Original deterministic learning packages for real Reader and note acceptance."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import zipfile

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256


@dataclass(frozen=True)
class ReaderFixture:
    archive: bytes
    course: dm.Course
    lessons: tuple[dm.Lesson, ...]
    blocks: tuple[dm.ContentBlock, ...]
    bodies: dict[str, str]


def ref(value: dm.Course | dm.Lesson | dm.ContentBlock) -> dm.ContentRef:
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def reader_fixture(prefix: str = "reader", revision: int = 1, *, citations: bool = True) -> ReaderFixture:
    """No documents, network, provider output or existing workspace are read."""
    if not prefix.isascii() or not prefix.isalpha() or revision not in {1, 2}:
        raise ValueError("Use an ASCII alphabetic fixture prefix and revision1/2")
    payloads: dict[str, bytes] = {}
    bodies: dict[str, str] = {}
    definitions = [
        ("definition", "definition", "定义：残差与损失", r"""# 残差与损失的定义

设参数 $\theta\in\mathbb{R}$，给定观测向量 $h=(1,2)$ 与 $y=(2,4)$。
残差为 $r_i=y_i-h_i\theta$，平方损失为 $L(\theta)=\sum_{i=1}^2r_i^2$。

选文甲 🧠 中文 café é：**强调内容** 与 `被动代码`。

重复句子用于选择定位。

中间段落保持原始换行和标点。

重复句子用于选择定位。
"""),
        ("proof", "proof", "证明：唯一最小点", r"""# 唯一性的完整证明

对任意实参数，逐项展开并配方：

$$L(\theta)=(2-\theta)^2+(4-2\theta)^2=20-20\theta+5\theta^2=5(\theta-2)^2.$$

实数平方非负，且平方为零当且仅当其底数为零。因此损失最小值为零，只在 $\theta=2$ 达到。
这里证明的是此给定平方目标的唯一最小点，不是任意噪声模型中的统计最优性。
"""),
        ("example", "worked_example", "例题：逐项计算与边界", r"""# 已知观测的逐项计算

条件为 $h=(1,2)$、$y=(2,4)$，未知参数为实数。

| 量 | 展开 | 结果 |
|---|---|---|
| $A$ | $1^2+2^2$ | $5$ |
| $B$ | $1\cdot2+2\cdot4$ | $10$ |
| $\hat\theta$ | $B/A$ | $2$ |

代回得预测 $(2,4)$、残差 $(0,0)$、损失零，与前述配方证明一致。
若两个 $h_i$ 都为零，损失不再依赖参数，不能宣称唯一估计。

下面仅展示长度较大的向量，以验证公式局部滚动：

$$v=(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40).$$

```python
# 合成示例代码仅作文本，不在 Reader 执行。
print("READER_CODE_MUST_STAY_PASSIVE")
```
"""),
        ("summary", "summary", "小结与阅读定位", "# 阅读小结\n\n" + "\n\n".join(
            f"定位段落 {number:02d}：本段是用于检验原生滚动回读的合成正文，阅读位置与已读确认分别保存。"
            for number in range(1, 35)
        )),
    ]
    citation = dm.Citation(id=f"citation_{prefix}", title="原创 Reader 验收材料", locator="tests/reader_fixtures.py",
                           verification="user_supplied")
    blocks = []
    for suffix, kind, title, body in definitions:
        identifier = f"block_{prefix}_{suffix}"
        if revision == 2 and suffix == "definition":
            body = body.replace("选文甲", "第二修订选文")
        path = f"content/{identifier}.r{revision}.md"
        data = body.encode("utf-8")
        block = dm.ContentBlock(id=identifier, revision=revision, kind=kind, title=title,
            body_path=path, body_sha256=sha256(data).hexdigest(), citations=[citation.id] if citations else [],
            depends_on=[ref(blocks[0])] if suffix in {"proof", "example"} else [])
        payloads[path] = data
        payloads[f"blocks/{identifier}.r{revision}.json"] = canonical_bytes(block)
        bodies[identifier] = body
        blocks.append(block)
    lessons = (
        dm.Lesson(id=f"lesson_{prefix}_reasoning", revision=revision, title="从定义到证明与例题的完整推导",
                  objectives=["核对条件、逐步计算与唯一性"], block_refs=[ref(block) for block in blocks[:3]]),
        dm.Lesson(id=f"lesson_{prefix}_review", revision=revision, title="长篇小结、原始选文与阅读位置",
                  objectives=["区分阅读位置和已读确认"], block_refs=[ref(blocks[3])]),
    )
    for lesson in lessons:
        payloads[f"lessons/{lesson.id}.r{revision}.json"] = canonical_bytes(lesson)
    course = dm.Course(id=f"course_{prefix}", revision=revision, title=f"原创阅读验收教材 {prefix}",
        audience="软件验收用合成内容", lesson_refs=[ref(lesson) for lesson in lessons],
        sections=[dm.CourseSection(id=f"section_{prefix}_core", title="第一章：模型、推导与算例",
                                  lesson_ids=[lessons[0].id]),
                  dm.CourseSection(id=f"section_{prefix}_review", title="第二章：小结与回读",
                                  lesson_ids=[lessons[1].id])])
    payloads["course.json"] = canonical_bytes(course)
    payloads["concepts.json"] = canonical_bytes([])
    payloads["symbols.json"] = canonical_bytes([])
    payloads["sources/citations.json"] = canonical_bytes([citation.model_dump(mode="json")] if citations else [])
    manifest = dm.Manifest(package_id=f"package_{prefix}_r{revision}", profile="learner", root_course="course.json",
        created_at="2026-09-14T00:00:00Z", files=[dm.FileEntry(path=path, sha256=sha256(data).hexdigest(), size=len(data),
            media_type="text/markdown" if path.endswith(".md") else "application/json", visibility="learner")
            for path, data in sorted(payloads.items())])
    payloads["manifest.json"] = canonical_bytes(manifest)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as package:
        for path, data in sorted(payloads.items()):
            member = zipfile.ZipInfo(path, date_time=(2026, 9, 14, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(member, data)
    return ReaderFixture(archive.getvalue(), course, lessons, tuple(blocks), bodies)


def reader_history_package(prefix: str = "reader") -> bytes:
    """One first import contains actual r1/r2 history without replacing any object."""
    older, newer = reader_fixture(prefix, 1), reader_fixture(prefix, 2)
    payloads: dict[str, bytes] = {}
    for number, fixture in [(1, older), (2, newer)]:
        with zipfile.ZipFile(BytesIO(fixture.archive)) as archive:
            for path in archive.namelist():
                if path == "manifest.json":
                    continue
                destination = f"courses/{fixture.course.id}.r1.json" if number == 1 and path == "course.json" else path
                value = archive.read(path)
                if destination in payloads and payloads[destination] != value:
                    raise ValueError("History fixture has inconsistent shared members")
                payloads[destination] = value
    manifest = dm.Manifest(package_id=f"package_{prefix}_history", profile="learner", root_course="course.json",
        created_at="2026-09-14T00:00:00Z", files=[dm.FileEntry(path=path, sha256=sha256(data).hexdigest(), size=len(data),
            media_type="text/markdown" if path.endswith(".md") else "application/json", visibility="learner")
            for path, data in sorted(payloads.items())])
    payloads["manifest.json"] = canonical_bytes(manifest)
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for path, data in sorted(payloads.items()):
            member = zipfile.ZipInfo(path, date_time=(2026, 9, 14, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, data)
    return output.getvalue()


if __name__ == "__main__":
    import sys
    sys.stdout.buffer.write(reader_fixture(*sys.argv[1:2]).archive)
