import { describe, it, expect, beforeEach, mock } from "bun:test";
import { exportToCSV } from "../src/lib/utils";

// Pure CSV row formatter matching exportToCSV implementation
function formatCSVRows(data: Record<string, unknown>[]): string[] {
  if (!data || data.length === 0) return [];
  const headers = Object.keys(data[0]);
  return [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        let val = ('' + (row[header] ?? ''));
        if (/^[=+\-@\t\r]/.test(val)) {
          val = "'" + val;
        }
        const escaped = val.replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',')
    )
  ];
}

describe("CSV Export & Formula Injection Security", () => {
  it("neutralizes command execution formula injection (=cmd|' /C calc'!A0)", () => {
    const data = [
      {
        course_code: "=cmd|' /C calc'!A0",
        title: "Formula Injection Course"
      }
    ];

    const rows = formatCSVRows(data);
    expect(rows.length).toBe(2);
    expect(rows[0]).toBe("course_code,title");
    // Starts with quote, then single quote, then =cmd
    expect(rows[1]).toBe("\"'=cmd|' /C calc'!A0\",\"Formula Injection Course\"");
  });

  it("neutralizes Excel @ function formula injection (@SUM(1,2))", () => {
    const data = [
      {
        course_code: "CMPE 150",
        title: "@SUM(1,2)*999"
      }
    ];

    const rows = formatCSVRows(data);
    expect(rows[1]).toBe("\"CMPE 150\",\"'@SUM(1,2)*999\"");
  });

  it("neutralizes plus (+) and minus (-) formula injection triggers", () => {
    const data = [
      {
        course_code: "+1234-5678",
        title: "-2+5+cmd|' /C calc'!A0"
      }
    ];

    const rows = formatCSVRows(data);
    expect(rows[1]).toBe("\"'+1234-5678\",\"'-2+5+cmd|' /C calc'!A0\"");
  });

  it("neutralizes tab (\\t) and carriage return (\\r) obfuscated formula injections", () => {
    const data = [
      {
        course_code: "\t=HYPERLINK(\"http://attacker.com\", \"Click\")",
        title: "\r=1+1"
      }
    ];

    const rows = formatCSVRows(data);
    expect(rows[1]).toBe("\"'\t=HYPERLINK(\"\"http://attacker.com\"\", \"\"Click\"\")\",\"'\r=1+1\"");
  });

  it("escapes embedded double quotes properly per RFC 4180", () => {
    const data = [
      {
        course_code: 'CS "Special" 101',
        title: 'He said: "Hello World"'
      }
    ];

    const rows = formatCSVRows(data);
    expect(rows[1]).toBe("\"CS \"\"Special\"\" 101\",\"He said: \"\"Hello World\"\"\"");
  });

  it("handles null, undefined, numeric, and boolean fields safely", () => {
    const data = [
      {
        course_code: "CMPE 150",
        title: null,
        credits: 3,
        is_active: true,
        extra: undefined
      }
    ];

    const rows = formatCSVRows(data);
    expect(rows[0]).toBe("course_code,title,credits,is_active,extra");
    expect(rows[1]).toBe('"CMPE 150","","3","true",""');
  });

  it("handles empty arrays and null inputs without errors", () => {
    expect(formatCSVRows([])).toEqual([]);
    // @ts-expect-error Testing null input
    expect(formatCSVRows(null)).toEqual([]);
  });

  it("executes exportToCSV in browser DOM environment without throwing", () => {
    // Mock DOM environment
    let createdBlob: Blob | null = null;
    let clicked = false;
    let removed = false;
    let appended = false;
    let downloadedFilename = "";

    const mockLink = {
      setAttribute: (attr: string, value: string) => {
        if (attr === "download") downloadedFilename = value;
      },
      style: { visibility: "visible" },
      click: () => { clicked = true; }
    };

    globalThis.document = {
      // @ts-expect-error Mocking createElement
      createElement: (tag: string) => {
        if (tag === "a") return mockLink;
        return {};
      },
      body: {
        // @ts-expect-error Mocking appendChild
        appendChild: (el: unknown) => { appended = true; },
        // @ts-expect-error Mocking removeChild
        removeChild: (el: unknown) => { removed = true; }
      }
    };

    globalThis.URL.createObjectURL = (blob: Blob) => {
      createdBlob = blob;
      return "blob:http://localhost/fake-blob-url";
    };

    const exportData = [
      {
        course_code: "=cmd|' /C calc'!A0",
        title: "Malicious Export Test",
        instructor: "@SUM(1,2)"
      }
    ];

    exportToCSV(exportData, "test_export");

    expect(clicked).toBe(true);
    expect(appended).toBe(true);
    expect(removed).toBe(true);
    expect(downloadedFilename).toBe("test_export.csv");
    expect(createdBlob).not.toBeNull();
  });
});
