const INVOICES = [
  ["INV-1048", "Harbor Lane Bakery", "Oct 28", "Nov 27", 1240.0, "Open"],
  ["INV-1047", "Quillon Test Studio", "Oct 26", "Nov 25", 3860.0, "Paid"],
  ["INV-1046", "Birch & Vale Cycles", "Oct 24", "Nov 23", 615.5, "Open"],
  ["INV-1045", "Sample Roofing Co.", "Sep 30", "Oct 15", 4120.0, "Overdue"],
  ["INV-1044", "Harbor Lane Bakery", "Sep 28", "Oct 28", 1240.0, "Paid"],
  ["INV-1043", "Tern Island Ferries", "Sep 22", "Oct 22", 8795.0, "Paid"],
  ["INV-1042", "Fictional Foods Ltd", "Sep 18", "Oct 18", 2354.4, "Overdue"],
  ["INV-1041", "Oakfield Demo School", "Sep 12", "Oct 12", 980.0, "Paid"],
  ["INV-1040", "Pixel Goat Games", "Sep 04", "Oct 04", 1475.0, "Paid"],
  ["INV-1039", "Lantern Row Books", "Aug 29", "Sep 28", 310.25, "Overdue"],
  ["INV-1038", "Quillon Test Studio", "Aug 26", "Sep 25", 3860.0, "Paid"],
  ["INV-1037", "Birch & Vale Cycles", "Aug 20", "Sep 19", 615.5, "Paid"],
  ["INV-1036", "Sample Roofing Co.", "Aug 14", "Sep 13", 2210.0, "Paid"],
  ["INV-1035", "Tern Island Ferries", "Aug 06", "Sep 05", 8795.0, "Paid"],
].map(([number, customer, issued, due, amount, status]) => ({ number, customer, issued, due, amount, status }));

const STATEMENTS = [
  ["January", 31240], ["February", 29870], ["March", 35410], ["April", 33120],
  ["May", 38990], ["June", 41050], ["July", 39720], ["August", 44380],
  ["September", 46120], ["October", 48250],
];

const ADDONS = [
  ["Reminder emails", "Chase late payers on a schedule you set.", 9],
  ["Team seats", "Five more people on the same account.", 25],
  ["Custom templates", "Your logo and colours on every invoice.", 12],
  ["Tax reports", "Quarterly summaries, ready for your accountant.", 15],
  ["Priority support", "A reply within four working hours.", 29],
  ["Client portal", "Customers see and pay invoices themselves.", 19],
].map(([name, description, price]) => ({ name, description, price }));

const LINE_ITEMS = [
  ["Monthly bookkeeping", 1, 950],
  ["Payroll runs", 4, 120],
  ["Cold storage audit", 6, 95],
  ["Delivery route review", 2, 142],
];

const REVENUE = [["May", 39], ["Jun", 41], ["Jul", 40], ["Aug", 44], ["Sep", 46], ["Oct", 48]];
