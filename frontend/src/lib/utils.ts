/**
 * Converts an array of objects into a CSV string and triggers a browser download.
 * @param data Array of objects to export
 * @param filename Name of the file (without extension)
 */
export function exportToCSV(data: any[], filename: string) {
  if (!data || data.length === 0) return;

  // Extract headers from the first object
  const headers = Object.keys(data[0]);
  
  // Create CSV rows
  const csvRows = [
    // Header row
    headers.join(','),
    // Data rows
    ...data.map(row => 
      headers.map(header => {
        let val = ('' + (row[header] ?? ''));
        // Neutralize CSV formula injection characters
        if (/^[=+\-@\t\r]/.test(val)) {
          val = "'" + val;
        }
        const escaped = val.replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',')
    )
  ];

  const csvContent = csvRows.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Maps Boğaziçi timetable slot numbers (1-14) to their standardized time intervals.
 * Slot 1: 09:00 - 10:00, ..., Slot 14: 22:00 - 23:00.
 */
export function formatSlotTime(hour: number | string | undefined | null): string {
  if (hour === undefined || hour === null) return "";
  const h = typeof hour === "string" ? parseInt(hour, 10) : hour;
  if (isNaN(h) || h < 1 || h > 14) return `Slot ${hour}`;
  const startHour = (8 + h).toString().padStart(2, "0");
  const endHour = (9 + h).toString().padStart(2, "0");
  return `${startHour}:00 - ${endHour}:00`;
}
