#!/usr/bin/env node
/**
 * MD to DOCX Converter
 * 将基于《格式规范》的 Markdown 文档转换为 Word 文档
 *
 * 格式规范：
 * - 标题字体：仿宋
 * - 正文字体：仿宋
 * - 行间距：最小 30pt
 * - + 自然段落：第1层首行缩进1cm，第n层左缩进n*1cm
 * - - 列表项：符号1cm，悬挂缩进1cm，第n层左缩进n*1cm
 */

const {
	Document,
	Packer,
	Paragraph,
	TextRun,
	Table,
	TableRow,
	TableCell,
	Header,
	Footer,
	AlignmentType,
	LevelFormat,
	HeadingLevel,
	BorderStyle,
	WidthType,
	ShadingType,
	PageNumber,
	ImageRun,
} = require("docx")
const fs = require("fs")
const path = require("path")
const puppeteer = require("puppeteer-core")

// 自动检测 Chrome 路径
function findChrome() {
	const possiblePaths = []

	if (process.platform === "win32") {
		// Windows
		const programFiles = process.env["PROGRAMFILES"] || "C:\\Program Files"
		const programFilesX86 = process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)"
		const localAppData = process.env["LOCALAPPDATA"] || ""

		possiblePaths.push(
			path.join(programFilesX86, "Google", "Chrome", "Application", "chrome.exe"),
			path.join(programFiles, "Google", "Chrome", "Application", "chrome.exe"),
			path.join(localAppData, "Google", "Chrome", "Application", "chrome.exe"),
			path.join(programFilesX86, "Microsoft", "Edge", "Application", "msedge.exe"),
			path.join(programFiles, "Microsoft", "Edge", "Application", "msedge.exe"),
		)
	} else if (process.platform === "darwin") {
		// macOS
		possiblePaths.push("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
	} else {
		// Linux
		possiblePaths.push("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium")
	}

	// 检查 puppeteer 缓存目录（跨平台）
	const homeDirs = [process.env["HOME"], process.env["USERPROFILE"], "/home/claude", "/root"].filter(Boolean)

	for (const homeDir of homeDirs) {
		const puppeteerCacheDir = path.join(homeDir, ".cache", "puppeteer", "chrome")
		if (fs.existsSync(puppeteerCacheDir)) {
			try {
				const versions = fs.readdirSync(puppeteerCacheDir)
				for (const ver of versions) {
					// Linux
					const chromePathLinux = path.join(puppeteerCacheDir, ver, "chrome-linux64", "chrome")
					if (fs.existsSync(chromePathLinux)) {
						possiblePaths.push(chromePathLinux)
					}
					// Windows
					const chromePathWin = path.join(puppeteerCacheDir, ver, "chrome-win64", "chrome.exe")
					if (fs.existsSync(chromePathWin)) {
						possiblePaths.push(chromePathWin)
					}
				}
			} catch (e) {}
		}
	}

	for (const p of possiblePaths) {
		if (p && fs.existsSync(p)) {
			console.log(`Found Chrome at: ${p}`)
			return p
		}
	}

	return null
}

const CHROME_PATH = findChrome()

// ============ 常量定义 ============
const FONT_HEADING = "FangSong" // 仿宋
const FONT_BODY = "FangSong" // 仿宋
const FONT_CODE = "FangSong" // 仿宋
const FONT_GRAPH = "Sarasa Term SC" // ASCII 文本图字体

const FONT_SIZE = 30 // 小三号字 = 15pt = 20 half-points
const FONT_SIZE_GRAPH = 24 // 图块字号 12pt = 24 half-points
const LINE_SPACING = 21 * 20 // 最小行高 30pt，转换为 twip (1pt = 20 twip)
const SPACING_BEFORE = 3 * 20 // 段前 6pt
const SPACING_AFTER = 6 * 20 // 段后 12pt
const CM_TO_TWIP = 567 // 1cm ≈ 567 twip
const FIRST_LEVEL_SPACING_BEFORE = 18 * 20 // 第一级段前 18pt

const INDENT_UNIT = CM_TO_TWIP // 1cm 缩进单位

// ============ ASCII 图转 PNG ============
async function convertAsciiToPng(asciiText, outputPath) {
	if (!CHROME_PATH) {
		console.warn("Warning: Chrome/Edge not found, ASCII graph will be kept as text")
		return null
	}

	const browser = await puppeteer.launch({
		headless: true,
		executablePath: CHROME_PATH,
		args: ["--no-sandbox", "--disable-setuid-sandbox"],
	})

	try {
		const page = await browser.newPage()

		// 创建 HTML 页面渲染 ASCII 图
		const html = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @font-face {
            font-family: 'Sarasa Term SC';
            src: local('Sarasa Term SC'), local('Sarasa-Term-SC');
        }
        body {
            margin: 0;
            padding: 20px;
            background: white;
        }
        pre {
            font-family: 'Sarasa Term SC', 'Consolas', 'Monaco', monospace;
            font-size: 14px;
            line-height: 1.4;
            margin: 0;
            white-space: pre;
            color: #333;
        }
    </style>
</head>
<body>
    <pre id="content">${asciiText.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
</body>
</html>`

		await page.setContent(html, { waitUntil: "networkidle0" })

		// 获取内容尺寸
		const contentBox = await page.evaluate(() => {
			const el = document.getElementById("content")
			const rect = el.getBoundingClientRect()
			return {
				width: Math.ceil(rect.width) + 40, // 加上 padding
				height: Math.ceil(rect.height) + 40,
			}
		})

		// 设置视口大小
		await page.setViewport({
			width: contentBox.width,
			height: contentBox.height,
			deviceScaleFactor: 2, // 高清截图
		})

		// 截图
		await page.screenshot({
			path: outputPath,
			type: "png",
			omitBackground: false,
			clip: {
				x: 0,
				y: 0,
				width: contentBox.width,
				height: contentBox.height,
			},
		})

		return {
			width: contentBox.width * 2, // 因为 deviceScaleFactor: 2
			height: contentBox.height * 2,
		}
	} finally {
		await browser.close()
	}
}

// 批量转换所有 ASCII 图
async function convertAllAsciiGraphs(nodes, tempDir) {
	const graphImages = new Map()
	let graphIndex = 0

	for (const node of nodes) {
		if (node.type === "graph_block" && node.language === "graph") {
			const imagePath = path.join(tempDir, `graph_${graphIndex}.png`)
			const dimensions = await convertAsciiToPng(node.content, imagePath)
			if (dimensions) {
				graphImages.set(graphIndex, {
					path: imagePath,
					width: dimensions.width,
					height: dimensions.height,
				})
				node.imageIndex = graphIndex
			}
			graphIndex++
		}
	}

	return graphImages
}

// ============ 节点类型 ============
const NodeType = {
	HEADING: "heading",
	CONTENT: "content", // + 开头
	LIST_ITEM: "list_item", // - 开头
	CODE_BLOCK: "code_block",
	GRAPH_BLOCK: "graph_block",
	TABLE: "table",
	TEXT: "text",
}

// ============ Markdown 解析器 ============
class MarkdownParser {
	constructor(content) {
		this.lines = content.split("\n")
		this.pos = 0
		this.nodes = []
	}

	parse() {
		while (this.pos < this.lines.length) {
			const node = this.parseLine()
			if (node) this.nodes.push(node)
		}
		return this.nodes
	}

	parseLine() {
		if (this.pos >= this.lines.length) return null

		const line = this.lines[this.pos]

		// 空行跳过
		if (!line.trim()) {
			this.pos++
			return null
		}

		const indent = line.length - line.trimStart().length
		const stripped = line.trim()

		// 标题
		if (stripped.startsWith("#")) {
			return this.parseHeading(stripped)
		}

		// 代码块/图块
		if (stripped.startsWith("```")) {
			return this.parseCodeBlock(indent, stripped)
		}

		// 表格
		if (stripped.startsWith("|")) {
			return this.parseTable(indent)
		}

		// + 开头的内容行
		if (stripped.startsWith("+")) {
			return this.parseContentLine(indent, stripped)
		}

		// - 开头的列表项
		if (stripped.startsWith("-") && !stripped.match(/^\|.*-.*\|$/)) {
			return this.parseListItem(indent, stripped)
		}

		// 其他文本
		this.pos++
		return { type: NodeType.TEXT, content: stripped, indent }
	}

	parseHeading(line) {
		const match = line.match(/^(#{1,6})\s+(.+)$/)
		if (match) {
			const level = match[1].length
			let content = match[2]
			// 去掉原有的编号（如 "1 标题" 或 "1.1 标题"），因为会自动生成
			content = content.replace(/^[\d.]+\s+/, "")
			this.pos++
			return { type: NodeType.HEADING, content, level }
		}
		this.pos++
		return { type: NodeType.TEXT, content: line, indent: 0 }
	}

	parseContentLine(indent, line) {
		const content = line.replace(/^\+\s*/, "")
		this.pos++
		return { type: NodeType.CONTENT, content, indent }
	}

	parseListItem(indent, line) {
		const content = line.replace(/^-\s*/, "")
		this.pos++
		return { type: NodeType.LIST_ITEM, content, indent }
	}

	parseCodeBlock(indent, firstLine) {
		const langMatch = firstLine.match(/^```(\w*)$/)
		const language = langMatch ? langMatch[1] : ""
		const isGraph = ["graph", "mermaid", "dot"].includes(language)

		this.pos++
		const lines = []

		while (this.pos < this.lines.length) {
			const line = this.lines[this.pos]
			if (line.trim() === "```") {
				this.pos++
				break
			}
			lines.push(line)
			this.pos++
		}

		return {
			type: isGraph ? NodeType.GRAPH_BLOCK : NodeType.CODE_BLOCK,
			content: lines.join("\n"),
			indent,
			language,
			rawLines: lines,
		}
	}

	parseTable(indent) {
		const lines = []

		while (this.pos < this.lines.length) {
			const line = this.lines[this.pos]
			if (!line.trim().startsWith("|")) break
			lines.push(line.trim())
			this.pos++
		}

		return { type: NodeType.TABLE, content: "", indent, rawLines: lines }
	}
}

// ============ 文档生成器 ============
class DocxGenerator {
	constructor(graphImages = new Map()) {
		this.graphImages = graphImages // 存储 ASCII 图转换后的图片信息

		// 样式配置
		this.styles = {
			default: {
				document: {
					run: { font: FONT_BODY, size: FONT_SIZE }, // 四号字 14pt
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
					},
				},
			},
			paragraphStyles: [
				{
					id: "Title",
					name: "Title",
					basedOn: "Normal",
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						alignment: AlignmentType.CENTER,
					},
				},
				{
					id: "Heading1",
					name: "Heading 1",
					basedOn: "Normal",
					next: "Normal",
					quickFormat: true,
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						outlineLevel: 0,
					},
				},
				{
					id: "Heading2",
					name: "Heading 2",
					basedOn: "Normal",
					next: "Normal",
					quickFormat: true,
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						outlineLevel: 1,
					},
				},
				{
					id: "Heading3",
					name: "Heading 3",
					basedOn: "Normal",
					next: "Normal",
					quickFormat: true,
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						outlineLevel: 2,
					},
				},
				{
					id: "Heading4",
					name: "Heading 4",
					basedOn: "Normal",
					next: "Normal",
					quickFormat: true,
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						outlineLevel: 3,
					},
				},
				{
					id: "Heading5",
					name: "Heading 5",
					basedOn: "Normal",
					next: "Normal",
					quickFormat: true,
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						outlineLevel: 4,
					},
				},
				{
					id: "Heading6",
					name: "Heading 6",
					basedOn: "Normal",
					next: "Normal",
					quickFormat: true,
					run: { size: FONT_SIZE, bold: true, font: FONT_HEADING },
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
						outlineLevel: 5,
					},
				},
			],
		}

		// 列表编号配置
		// 第 n 层（从0开始）：左缩进 (n+1)*1cm，悬挂缩进 1cm
		this.numbering = {
			config: [
				{
					reference: "bullet-list",
					levels: this.generateListLevels(),
				},
				{
					reference: "heading-numbering",
					levels: this.generateHeadingNumberingLevels(),
				},
			],
		}

		// 表格边框
		this.tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "000000" }
		this.cellBorders = {
			top: this.tableBorder,
			bottom: this.tableBorder,
			left: this.tableBorder,
			right: this.tableBorder,
		}
	}

	// 生成列表级别配置
	generateListLevels() {
		const levels = []
		for (let i = 0; i <= 8; i++) {
			// 第 n 层（从0开始）：左缩进 (n+1)*1cm，悬挂缩进 1cm
			const leftIndent = (i + 1) * INDENT_UNIT
			const hangingIndent = INDENT_UNIT

			levels.push({
				level: i,
				format: LevelFormat.BULLET,
				text: "-",
				alignment: AlignmentType.LEFT,
				style: {
					paragraph: {
						indent: {
							left: leftIndent,
							hanging: hangingIndent,
						},
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
					},
					run: { font: FONT_BODY, size: FONT_SIZE },
				},
			})
		}
		return levels
	}

	// 生成标题编号级别配置
	// 从二级标题开始编号：1、1.1、1.1.1、1.1.1.1、1.1.1.1.1
	generateHeadingNumberingLevels() {
		const levels = []

		for (let i = 0; i <= 5; i++) {
			// 构建编号文本格式：1、1.1、1.1.1 等
			let text = ""
			for (let j = 0; j <= i; j++) {
				text += `%${j + 1}`
				if (j < i) text += "."
			}
			text += " " // 编号后加空格

			levels.push({
				level: i,
				format: LevelFormat.DECIMAL,
				text: text,
				alignment: AlignmentType.LEFT,
				style: {
					paragraph: {
						spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
					},
					run: {
						font: FONT_HEADING,
						size: FONT_SIZE,
						bold: true,
					},
				},
			})
		}
		return levels
	}

	// 解析表格数据
	parseTableData(lines) {
		const rows = []
		for (const line of lines) {
			// 跳过分隔行
			if (line.match(/^\|[\s\-:|]+\|$/)) continue

			const cells = line
				.split("|")
				.slice(1, -1)
				.map(cell => cell.trim())

			if (cells.length > 0) {
				rows.push(cells)
			}
		}
		return rows
	}

	// 创建表格
	// indentLevel: 表格所在层级 n
	createTable(rows, indentLevel = 0) {
		if (rows.length === 0) return null

		// 表格整体缩进 (n*1 + 0.2)cm，宽度 (15.5 - n*1)cm
		const tableIndent = Math.round((indentLevel * 1 + 0.2) * CM_TO_TWIP)
		const tableWidth = Math.round((15.5 - indentLevel * 1) * CM_TO_TWIP)

		const numCols = rows[0].length
		const colWidth = Math.floor(tableWidth / numCols)
		const columnWidths = Array(numCols).fill(colWidth)

		// 单元格边距：左右 0.2cm，上 0，下 0.1cm
		const cellMargin = {
			top: 0,
			bottom: Math.round(0.1 * CM_TO_TWIP), // 0.1cm
			left: Math.round(0.2 * CM_TO_TWIP), // 0.2cm
			right: Math.round(0.2 * CM_TO_TWIP), // 0.2cm
		}

		const tableRows = rows.map((row, rowIndex) => {
			const isHeaderRow = rowIndex === 0
			return new TableRow({
				tableHeader: isHeaderRow,
				children: row.map(
					cell =>
						new TableCell({
							borders: this.cellBorders,
							width: { size: colWidth, type: WidthType.DXA },
							shading: isHeaderRow ? { fill: "E7E6E6", type: ShadingType.CLEAR } : undefined,
							margins: cellMargin,
							children: [
								new Paragraph({
									alignment: AlignmentType.LEFT,
									spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
									children: [
										new TextRun({
											text: cell,
											bold: isHeaderRow,
											font: isHeaderRow ? FONT_HEADING : FONT_BODY,
											size: FONT_SIZE,
										}),
									],
								}),
							],
						}),
				),
			})
		})

		return new Table({
			columnWidths,
			rows: tableRows,
			indent: {
				size: tableIndent,
				type: WidthType.DXA,
			},
			width: {
				size: tableWidth,
				type: WidthType.DXA,
			},
		})
	}

	// 解析内联格式
	parseInlineFormatting(text, font = FONT_BODY) {
		const runs = []
		let lastIndex = 0

		// 匹配 **粗体**、*斜体*、`代码`
		const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`([^`]+)`)/g
		let match

		while ((match = regex.exec(text)) !== null) {
			// 添加匹配前的普通文本
			if (match.index > lastIndex) {
				runs.push(
					new TextRun({
						text: text.slice(lastIndex, match.index),
						font: font,
						size: FONT_SIZE,
					}),
				)
			}

			if (match[2]) {
				// 粗体
				runs.push(new TextRun({ text: match[2], bold: true, font: font, size: FONT_SIZE }))
			} else if (match[4]) {
				// 斜体
				runs.push(new TextRun({ text: match[4], italics: true, font: font, size: FONT_SIZE }))
			} else if (match[6]) {
				// 代码
				runs.push(new TextRun({ text: match[6], font: FONT_CODE, size: FONT_SIZE }))
			}

			lastIndex = match.index + match[0].length
		}

		// 添加剩余文本
		if (lastIndex < text.length) {
			runs.push(new TextRun({ text: text.slice(lastIndex), font: font, size: FONT_SIZE }))
		}

		// 如果没有任何格式，返回纯文本
		if (runs.length === 0) {
			runs.push(new TextRun({ text, font: font, size: FONT_SIZE }))
		}

		return runs
	}

	// 获取标题级别
	getHeadingLevel(level) {
		const levels = {
			1: HeadingLevel.HEADING_1,
			2: HeadingLevel.HEADING_2,
			3: HeadingLevel.HEADING_3,
			4: HeadingLevel.HEADING_4,
			5: HeadingLevel.HEADING_5,
			6: HeadingLevel.HEADING_6,
		}
		return levels[level] || HeadingLevel.HEADING_6
	}

	// 生成文档内容
	generateChildren(nodes) {
		const children = []
		let prevNodeType = null // 记录前一个节点类型

		for (let i = 0; i < nodes.length; i++) {
			const node = nodes[i]

			switch (node.type) {
				case NodeType.HEADING:
					// 标题段前间距：前一个也是标题则 6pt，否则 18pt
					const headingSpacingBefore = prevNodeType === NodeType.HEADING ? SPACING_BEFORE : FIRST_LEVEL_SPACING_BEFORE

					if (node.level === 1) {
						// 一级标题是文档标题，不参与编号，居中显示
						children.push(
							new Paragraph({
								heading: HeadingLevel.HEADING_1,
								alignment: AlignmentType.CENTER,
								spacing: { before: headingSpacingBefore, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								children: [new TextRun({ text: node.content, font: FONT_HEADING, bold: true, size: FONT_SIZE })],
							}),
						)
					} else {
						// 二级及以下标题使用自动编号
						const headingLevel = node.level - 2 // 转为 0-based，从二级开始
						children.push(
							new Paragraph({
								heading: this.getHeadingLevel(node.level),
								numbering: { reference: "heading-numbering", level: Math.min(headingLevel, 5) },
								spacing: { before: headingSpacingBefore, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								children: [new TextRun({ text: node.content, font: FONT_HEADING, bold: true, size: FONT_SIZE })],
							}),
						)
					}
					prevNodeType = NodeType.HEADING
					break

				case NodeType.CONTENT:
					// + 自然段落
					// 第0层（indent=0）：首行缩进 1cm，无左缩进，段前 18pt
					// 第n层（indent=n*4空格）：左缩进 n*1cm，无首行缩进
					const contentLevel = Math.floor(node.indent / 4)

					let contentIndent
					let contentSpacing
					if (contentLevel === 0) {
						// 第一层：首行缩进 1cm，段前 18pt
						contentIndent = { firstLine: INDENT_UNIT }
						contentSpacing = { before: FIRST_LEVEL_SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" }
					} else {
						// 第n层：左缩进 n*1cm
						contentIndent = { left: contentLevel * INDENT_UNIT }
						contentSpacing = { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" }
					}

					children.push(
						new Paragraph({
							indent: contentIndent,
							spacing: contentSpacing,
							children: this.parseInlineFormatting(node.content),
						}),
					)
					prevNodeType = NodeType.CONTENT
					break

				case NodeType.LIST_ITEM:
					// - 列表项
					// 第n层：左缩进 (n+1)*1cm，悬挂缩进 1cm
					// 第一级（n=0）段前 18pt
					const listLevel = Math.floor(node.indent / 4)
					const listSpacing =
						listLevel === 0
							? { before: FIRST_LEVEL_SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" }
							: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" }

					children.push(
						new Paragraph({
							numbering: { reference: "bullet-list", level: Math.min(listLevel, 8) },
							spacing: listSpacing,
							children: this.parseInlineFormatting(node.content),
						}),
					)
					prevNodeType = NodeType.LIST_ITEM
					break

				case NodeType.CODE_BLOCK:
					// 代码块标题
					children.push(
						new Paragraph({
							spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
							shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
							border: { top: { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" } },
							children: [
								new TextRun({
									text: `[${node.language || "text"}]`,
									font: FONT_CODE,
									size: FONT_SIZE,
									color: "666666",
								}),
							],
						}),
					)

					// 代码行
					for (const line of node.rawLines) {
						children.push(
							new Paragraph({
								shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
								spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								children: [new TextRun({ text: line || " ", font: FONT_CODE, size: FONT_SIZE })],
							}),
						)
					}

					// 代码块结束
					children.push(
						new Paragraph({
							shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
							border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" } },
							spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
							children: [],
						}),
					)
					prevNodeType = NodeType.CODE_BLOCK
					break

				case NodeType.GRAPH_BLOCK:
					// 检查是否有转换后的图片
					if (node.language === "graph" && node.imageIndex !== undefined && this.graphImages.has(node.imageIndex)) {
						const imgInfo = this.graphImages.get(node.imageIndex)
						const imageData = fs.readFileSync(imgInfo.path)

						// 计算图片在文档中的显示尺寸（限制最大宽度为 15cm）
						const maxWidth = 15 * 37.8 // 15cm in pixels (约 37.8 px/cm)
						let displayWidth = imgInfo.width / 2 // 因为 deviceScaleFactor: 2
						let displayHeight = imgInfo.height / 2

						if (displayWidth > maxWidth) {
							const scale = maxWidth / displayWidth
							displayWidth = maxWidth
							displayHeight = displayHeight * scale
						}

						// 插入图片
						children.push(
							new Paragraph({
								spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								alignment: AlignmentType.CENTER,
								children: [
									new ImageRun({
										type: "png",
										data: imageData,
										transformation: {
											width: Math.round(displayWidth),
											height: Math.round(displayHeight),
										},
									}),
								],
							}),
						)
					} else {
						// 非 graph 类型或没有图片，保持文本输出
						// 图块标题
						children.push(
							new Paragraph({
								spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								alignment: AlignmentType.CENTER,
								children: [
									new TextRun({
										text: `[${node.language}]`,
										font: FONT_GRAPH,
										size: FONT_SIZE_GRAPH,
										color: "666666",
										italics: true,
									}),
								],
							}),
						)

						// 图块内容（等宽字体居中）
						for (const line of node.rawLines) {
							children.push(
								new Paragraph({
									alignment: AlignmentType.CENTER,
									spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
									children: [new TextRun({ text: line || " ", font: FONT_GRAPH, size: FONT_SIZE_GRAPH })],
								}),
							)
						}

						children.push(
							new Paragraph({
								spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								children: [],
							}),
						)
					}
					prevNodeType = NodeType.GRAPH_BLOCK
					break

				case NodeType.TABLE:
					const tableLevel = Math.floor(node.indent / 4)
					const tableData = this.parseTableData(node.rawLines)
					const table = this.createTable(tableData, tableLevel)
					if (table) {
						children.push(table)
						children.push(
							new Paragraph({
								spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								children: [],
							}),
						)
					}
					prevNodeType = NodeType.TABLE
					break

				case NodeType.TEXT:
					if (node.content.trim()) {
						children.push(
							new Paragraph({
								spacing: { before: SPACING_BEFORE, after: SPACING_AFTER, line: LINE_SPACING, lineRule: "atLeast" },
								children: this.parseInlineFormatting(node.content),
							}),
						)
					}
					prevNodeType = NodeType.TEXT
					break
			}
		}

		return children
	}

	// 生成文档
	generate(nodes) {
		const children = this.generateChildren(nodes)

		return new Document({
			styles: this.styles,
			numbering: this.numbering,
			sections: [
				{
					properties: {
						page: {
							margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
						},
					},
					headers: {
						default: new Header({
							children: [
								new Paragraph({
									alignment: AlignmentType.RIGHT,
									spacing: { line: LINE_SPACING, lineRule: "atLeast" },
									children: [new TextRun({ text: "", size: 18, color: "999999", font: FONT_BODY })],
								}),
							],
						}),
					},
					footers: {
						default: new Footer({
							children: [
								new Paragraph({
									alignment: AlignmentType.CENTER,
									spacing: { line: LINE_SPACING, lineRule: "atLeast" },
									children: [
										new TextRun({ text: "- ", font: FONT_BODY, size: FONT_SIZE }),
										new TextRun({ children: [PageNumber.CURRENT], font: FONT_BODY, size: FONT_SIZE }),
										new TextRun({ text: " -", font: FONT_BODY, size: FONT_SIZE }),
									],
								}),
							],
						}),
					},
					children,
				},
			],
		})
	}
}

// ============ 主函数 ============
async function convert(inputPath, outputPath) {
	if (!fs.existsSync(inputPath)) {
		console.error(`Error: File not found: ${inputPath}`)
		process.exit(1)
	}

	const content = fs.readFileSync(inputPath, "utf-8")

	const parser = new MarkdownParser(content)
	const nodes = parser.parse()
	console.log(`Parsed ${nodes.length} nodes from ${inputPath}`)

	// 创建临时目录存放图片
	const os = require("os")
	const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "md2docx-"))

	try {
		// 转换所有 ASCII 图为 PNG
		console.log("Converting ASCII graphs to images...")
		const graphImages = await convertAllAsciiGraphs(nodes, tempDir)
		console.log(`Converted ${graphImages.size} graph(s)`)

		const generator = new DocxGenerator(graphImages)
		const doc = generator.generate(nodes)

		const buffer = await Packer.toBuffer(doc)
		fs.writeFileSync(outputPath, buffer)
		console.log(`Document created: ${outputPath}`)
	} finally {
		// 清理临时文件
		try {
			const files = fs.readdirSync(tempDir)
			for (const file of files) {
				fs.unlinkSync(path.join(tempDir, file))
			}
			fs.rmdirSync(tempDir)
		} catch (e) {
			// 忽略清理错误
		}
	}
}

// ============ 命令行入口 ============
function main() {
	const args = process.argv.slice(2)

	if (args.length === 0) {
		console.log("Usage: node md2docx.js <input.md> [output.docx]")
		console.log("\n将基于《格式规范》的 Markdown 文档转换为 Word 文档")
		console.log("\n格式规范：")
		console.log("  - 字体：仿宋")
		console.log("  - 行间距：最小 30pt")
		console.log("  - 段前 6pt，段后 12pt")
		console.log("  - + 自然段落：第1层首行缩进1cm，第n层左缩进n×1cm")
		console.log("  - - 列表项：悬挂缩进1cm，第n层左缩进(n+1)×1cm")
		console.log("  - ```graph ASCII 图自动转换为 PNG 图片")
		process.exit(1)
	}

	const inputPath = args[0]
	const outputPath = args[1] || inputPath.replace(/\.md$/i, ".docx")

	convert(inputPath, outputPath).catch(err => {
		console.error("Error:", err.message)
		process.exit(1)
	})
}

main()
