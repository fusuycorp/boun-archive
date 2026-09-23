/**
 * Official Boğaziçi University Academic Schedule Registry
 * Sourced directly from OBIKAS & registration.boun.edu.tr/scripts/sch.asp
 */

export interface OfficialDepartment {
  kisaadi: string;
  bolum: string;
  name: string;
}

export interface OfficialSemester {
  value: string;
  label: string;
}

export const OFFICIAL_SCHEDULE_BASE = "https://registration.boun.edu.tr/scripts/sch.asp";

export function buildOfficialScheduleUrl(donem: string, kisaadi: string, bolum: string): string {
  return `${OFFICIAL_SCHEDULE_BASE}?donem=${encodeURIComponent(donem)}&kisaadi=${encodeURIComponent(kisaadi)}&bolum=${bolum}`;
}

export const OFFICIAL_SEMESTERS: OfficialSemester[] = [
  {
    "value": "2026/2027-1",
    "label": "2026/2027 - Fall (1)"
  },
  {
    "value": "2025/2026-3",
    "label": "2025/2026 - Summer (3)"
  },
  {
    "value": "2025/2026-2",
    "label": "2025/2026 - Spring (2)"
  },
  {
    "value": "2025/2026-1",
    "label": "2025/2026 - Fall (1)"
  },
  {
    "value": "2024/2025-3",
    "label": "2024/2025 - Summer (3)"
  },
  {
    "value": "2024/2025-2",
    "label": "2024/2025 - Spring (2)"
  },
  {
    "value": "2024/2025-1",
    "label": "2024/2025 - Fall (1)"
  },
  {
    "value": "2023/2024-3",
    "label": "2023/2024 - Summer (3)"
  },
  {
    "value": "2023/2024-2",
    "label": "2023/2024 - Spring (2)"
  },
  {
    "value": "2023/2024-1",
    "label": "2023/2024 - Fall (1)"
  },
  {
    "value": "2022/2023-3",
    "label": "2022/2023 - Summer (3)"
  },
  {
    "value": "2022/2023-2",
    "label": "2022/2023 - Spring (2)"
  },
  {
    "value": "2022/2023-1",
    "label": "2022/2023 - Fall (1)"
  },
  {
    "value": "2021/2022-3",
    "label": "2021/2022 - Summer (3)"
  },
  {
    "value": "2021/2022-2",
    "label": "2021/2022 - Spring (2)"
  },
  {
    "value": "2021/2022-1",
    "label": "2021/2022 - Fall (1)"
  },
  {
    "value": "2020/2021-3",
    "label": "2020/2021 - Summer (3)"
  },
  {
    "value": "2020/2021-2",
    "label": "2020/2021 - Spring (2)"
  },
  {
    "value": "2020/2021-1",
    "label": "2020/2021 - Fall (1)"
  },
  {
    "value": "2019/2020-3",
    "label": "2019/2020 - Summer (3)"
  },
  {
    "value": "2019/2020-2",
    "label": "2019/2020 - Spring (2)"
  },
  {
    "value": "2019/2020-1",
    "label": "2019/2020 - Fall (1)"
  },
  {
    "value": "2018/2019-3",
    "label": "2018/2019 - Summer (3)"
  },
  {
    "value": "2018/2019-2",
    "label": "2018/2019 - Spring (2)"
  },
  {
    "value": "2018/2019-1",
    "label": "2018/2019 - Fall (1)"
  },
  {
    "value": "2017/2018-3",
    "label": "2017/2018 - Summer (3)"
  },
  {
    "value": "2017/2018-2",
    "label": "2017/2018 - Spring (2)"
  },
  {
    "value": "2017/2018-1",
    "label": "2017/2018 - Fall (1)"
  },
  {
    "value": "2016/2017-3",
    "label": "2016/2017 - Summer (3)"
  },
  {
    "value": "2016/2017-2",
    "label": "2016/2017 - Spring (2)"
  },
  {
    "value": "2016/2017-1",
    "label": "2016/2017 - Fall (1)"
  },
  {
    "value": "2015/2016-3",
    "label": "2015/2016 - Summer (3)"
  },
  {
    "value": "2015/2016-2",
    "label": "2015/2016 - Spring (2)"
  },
  {
    "value": "2015/2016-1",
    "label": "2015/2016 - Fall (1)"
  },
  {
    "value": "2014/2015-3",
    "label": "2014/2015 - Summer (3)"
  },
  {
    "value": "2014/2015-2",
    "label": "2014/2015 - Spring (2)"
  },
  {
    "value": "2014/2015-1",
    "label": "2014/2015 - Fall (1)"
  },
  {
    "value": "2013/2014-3",
    "label": "2013/2014 - Summer (3)"
  },
  {
    "value": "2013/2014-2",
    "label": "2013/2014 - Spring (2)"
  },
  {
    "value": "2013/2014-1",
    "label": "2013/2014 - Fall (1)"
  },
  {
    "value": "2012/2013-3",
    "label": "2012/2013 - Summer (3)"
  },
  {
    "value": "2012/2013-2",
    "label": "2012/2013 - Spring (2)"
  },
  {
    "value": "2012/2013-1",
    "label": "2012/2013 - Fall (1)"
  },
  {
    "value": "2011/2012-3",
    "label": "2011/2012 - Summer (3)"
  },
  {
    "value": "2011/2012-2",
    "label": "2011/2012 - Spring (2)"
  },
  {
    "value": "2011/2012-1",
    "label": "2011/2012 - Fall (1)"
  },
  {
    "value": "2010/2011-3",
    "label": "2010/2011 - Summer (3)"
  },
  {
    "value": "2010/2011-2",
    "label": "2010/2011 - Spring (2)"
  },
  {
    "value": "2010/2011-1",
    "label": "2010/2011 - Fall (1)"
  },
  {
    "value": "2009/2010-3",
    "label": "2009/2010 - Summer (3)"
  },
  {
    "value": "2009/2010-2",
    "label": "2009/2010 - Spring (2)"
  },
  {
    "value": "2009/2010-1",
    "label": "2009/2010 - Fall (1)"
  },
  {
    "value": "2008/2009-3",
    "label": "2008/2009 - Summer (3)"
  },
  {
    "value": "2008/2009-2",
    "label": "2008/2009 - Spring (2)"
  },
  {
    "value": "2008/2009-1",
    "label": "2008/2009 - Fall (1)"
  },
  {
    "value": "2007/2008-3",
    "label": "2007/2008 - Summer (3)"
  },
  {
    "value": "2007/2008-2",
    "label": "2007/2008 - Spring (2)"
  },
  {
    "value": "2007/2008-1",
    "label": "2007/2008 - Fall (1)"
  },
  {
    "value": "2006/2007-3",
    "label": "2006/2007 - Summer (3)"
  },
  {
    "value": "2006/2007-2",
    "label": "2006/2007 - Spring (2)"
  },
  {
    "value": "2006/2007-1",
    "label": "2006/2007 - Fall (1)"
  },
  {
    "value": "2005/2006-3",
    "label": "2005/2006 - Summer (3)"
  },
  {
    "value": "2005/2006-2",
    "label": "2005/2006 - Spring (2)"
  },
  {
    "value": "2005/2006-1",
    "label": "2005/2006 - Fall (1)"
  },
  {
    "value": "2004/2005-3",
    "label": "2004/2005 - Summer (3)"
  },
  {
    "value": "2004/2005-2",
    "label": "2004/2005 - Spring (2)"
  },
  {
    "value": "2004/2005-1",
    "label": "2004/2005 - Fall (1)"
  },
  {
    "value": "2003/2004-3",
    "label": "2003/2004 - Summer (3)"
  },
  {
    "value": "2003/2004-2",
    "label": "2003/2004 - Spring (2)"
  },
  {
    "value": "2003/2004-1",
    "label": "2003/2004 - Fall (1)"
  },
  {
    "value": "2002/2003-3",
    "label": "2002/2003 - Summer (3)"
  },
  {
    "value": "2002/2003-2",
    "label": "2002/2003 - Spring (2)"
  },
  {
    "value": "2002/2003-1",
    "label": "2002/2003 - Fall (1)"
  },
  {
    "value": "2001/2002-3",
    "label": "2001/2002 - Summer (3)"
  },
  {
    "value": "2001/2002-2",
    "label": "2001/2002 - Spring (2)"
  },
  {
    "value": "2001/2002-1",
    "label": "2001/2002 - Fall (1)"
  },
  {
    "value": "2000/2001-3",
    "label": "2000/2001 - Summer (3)"
  },
  {
    "value": "2000/2001-2",
    "label": "2000/2001 - Spring (2)"
  },
  {
    "value": "2000/2001-1",
    "label": "2000/2001 - Fall (1)"
  },
  {
    "value": "1999/2000-3",
    "label": "1999/2000 - Summer (3)"
  },
  {
    "value": "1999/2000-2",
    "label": "1999/2000 - Spring (2)"
  },
  {
    "value": "1999/2000-1",
    "label": "1999/2000 - Fall (1)"
  }
];

export const OFFICIAL_DEPARTMENTS: OfficialDepartment[] = [
  {
    "kisaadi": "ASIA",
    "bolum": "ASIAN+STUDIES",
    "name": "ASIAN STUDIES"
  },
  {
    "kisaadi": "ASIA",
    "bolum": "ASIAN+STUDIES+WITH+THESIS",
    "name": "ASIAN STUDIES WITH THESIS"
  },
  {
    "kisaadi": "ATA",
    "bolum": "ATATURK+INSTITUTE+FOR+MODERN+TURKISH+HISTORY",
    "name": "ATATURK INSTITUTE FOR MODERN TURKISH HISTORY"
  },
  {
    "kisaadi": "BM",
    "bolum": "BIOMEDICAL+ENGINEERING",
    "name": "BIOMEDICAL ENGINEERING"
  },
  {
    "kisaadi": "BIS",
    "bolum": "BUSINESS+INFORMATION+SYSTEMS",
    "name": "BUSINESS INFORMATION SYSTEMS"
  },
  {
    "kisaadi": "BIS",
    "bolum": "BUSINESS+INFORMATION+SYSTEMS+(WITH+THESIS)",
    "name": "BUSINESS INFORMATION SYSTEMS (WITH THESIS)"
  },
  {
    "kisaadi": "CHE",
    "bolum": "CHEMICAL+ENGINEERING",
    "name": "CHEMICAL ENGINEERING"
  },
  {
    "kisaadi": "CHEM",
    "bolum": "CHEMISTRY",
    "name": "CHEMISTRY"
  },
  {
    "kisaadi": "CE",
    "bolum": "CIVIL+ENGINEERING",
    "name": "CIVIL ENGINEERING"
  },
  {
    "kisaadi": "COGS",
    "bolum": "COGNITIVE+SCIENCE",
    "name": "COGNITIVE SCIENCE"
  },
  {
    "kisaadi": "CSE",
    "bolum": "COMPUTATIONAL+SCIENCE+%26+ENGINEERING",
    "name": "COMPUTATIONAL SCIENCE & ENGINEERING"
  },
  {
    "kisaadi": "CET",
    "bolum": "COMPUTER+EDUCATION+%26+EDUCATIONAL+TECHNOLOGY",
    "name": "COMPUTER EDUCATION & EDUCATIONAL TECHNOLOGY"
  },
  {
    "kisaadi": "CMPE",
    "bolum": "COMPUTER+ENGINEERING",
    "name": "COMPUTER ENGINEERING"
  },
  {
    "kisaadi": "INT",
    "bolum": "CONFERENCE+INTERPRETING",
    "name": "CONFERENCE INTERPRETING"
  },
  {
    "kisaadi": "CEM",
    "bolum": "CONSTRUCTION+ENGINEERING+AND+MANAGEMENT",
    "name": "CONSTRUCTION ENGINEERING AND MANAGEMENT"
  },
  {
    "kisaadi": "DSAI",
    "bolum": "DATA+SCIENCE+AND+ARTIFICIAL+INTELLIGENCE",
    "name": "DATA SCIENCE AND ARTIFICIAL INTELLIGENCE"
  },
  {
    "kisaadi": "PRED",
    "bolum": "EARLY+CHILDHOOD+EDUCATION",
    "name": "EARLY CHILDHOOD EDUCATION"
  },
  {
    "kisaadi": "EQE",
    "bolum": "EARTHQUAKE+ENGINEERING",
    "name": "EARTHQUAKE ENGINEERING"
  },
  {
    "kisaadi": "EC",
    "bolum": "ECONOMICS",
    "name": "ECONOMICS"
  },
  {
    "kisaadi": "EF",
    "bolum": "ECONOMICS+AND+FINANCE",
    "name": "ECONOMICS AND FINANCE"
  },
  {
    "kisaadi": "ED",
    "bolum": "EDUCATIONAL+SCIENCES",
    "name": "EDUCATIONAL SCIENCES"
  },
  {
    "kisaadi": "CET",
    "bolum": "EDUCATIONAL+TECHNOLOGY",
    "name": "EDUCATIONAL TECHNOLOGY"
  },
  {
    "kisaadi": "EE",
    "bolum": "ELECTRICAL+%26+ELECTRONICS+ENGINEERING",
    "name": "ELECTRICAL & ELECTRONICS ENGINEERING"
  },
  {
    "kisaadi": "ETM",
    "bolum": "ENGINEERING+AND+TECHNOLOGY+MANAGEMENT",
    "name": "ENGINEERING AND TECHNOLOGY MANAGEMENT"
  },
  {
    "kisaadi": "LL",
    "bolum": "ENGLISH+LITERATURE",
    "name": "ENGLISH LITERATURE"
  },
  {
    "kisaadi": "ENV",
    "bolum": "ENVIRONMENTAL+SCIENCES",
    "name": "ENVIRONMENTAL SCIENCES"
  },
  {
    "kisaadi": "ENVT",
    "bolum": "ENVIRONMENTAL+TECHNOLOGY",
    "name": "ENVIRONMENTAL TECHNOLOGY"
  },
  {
    "kisaadi": "XMBA",
    "bolum": "EXECUTIVE+MBA",
    "name": "EXECUTIVE MBA"
  },
  {
    "kisaadi": "FILM",
    "bolum": "FILM+AND+MEDIA+STUDIES",
    "name": "FILM AND MEDIA STUDIES"
  },
  {
    "kisaadi": "FE",
    "bolum": "FINANCIAL+ENGINEERING",
    "name": "FINANCIAL ENGINEERING"
  },
  {
    "kisaadi": "PA",
    "bolum": "FINE+ARTS",
    "name": "FINE ARTS"
  },
  {
    "kisaadi": "FLED",
    "bolum": "FOREIGN+LANGUAGE+EDUCATION",
    "name": "FOREIGN LANGUAGE EDUCATION"
  },
  {
    "kisaadi": "GED",
    "bolum": "GEODESY",
    "name": "GEODESY"
  },
  {
    "kisaadi": "GPH",
    "bolum": "GEOPHYSICS",
    "name": "GEOPHYSICS"
  },
  {
    "kisaadi": "GUID",
    "bolum": "GUIDANCE+%26+PSYCHOLOGICAL+COUNSELING",
    "name": "GUIDANCE & PSYCHOLOGICAL COUNSELING"
  },
  {
    "kisaadi": "HIST",
    "bolum": "HISTORY",
    "name": "HISTORY"
  },
  {
    "kisaadi": "HUM",
    "bolum": "HUMANITIES+COURSES+COORDINATOR",
    "name": "HUMANITIES COURSES COORDINATOR"
  },
  {
    "kisaadi": "IE",
    "bolum": "INDUSTRIAL+ENGINEERING",
    "name": "INDUSTRIAL ENGINEERING"
  },
  {
    "kisaadi": "MIR",
    "bolum": "INTERNATIONAL+RELATIONS%3aTURKEY%2cEUROPE+AND+THE+MIDDLE+EAST",
    "name": "INTERNATIONAL RELATIONS:TURKEY,EUROPE AND THE MIDDLE EAST"
  },
  {
    "kisaadi": "MIR",
    "bolum": "INTERNATIONAL+RELATIONS%3aTURKEY%2cEUROPE+AND+THE+MIDDLE+EAST+WITH+THESIS",
    "name": "INTERNATIONAL RELATIONS:TURKEY,EUROPE AND THE MIDDLE EAST WITH THESIS"
  },
  {
    "kisaadi": "INTT",
    "bolum": "INTERNATIONAL+TRADE",
    "name": "INTERNATIONAL TRADE"
  },
  {
    "kisaadi": "INTT",
    "bolum": "INTERNATIONAL+TRADE+MANAGEMENT",
    "name": "INTERNATIONAL TRADE MANAGEMENT"
  },
  {
    "kisaadi": "LAW",
    "bolum": "LAW+PR.",
    "name": "LAW PR."
  },
  {
    "kisaadi": "LS",
    "bolum": "LEARNING+SCIENCES",
    "name": "LEARNING SCIENCES"
  },
  {
    "kisaadi": "LING",
    "bolum": "LINGUISTICS",
    "name": "LINGUISTICS"
  },
  {
    "kisaadi": "AD",
    "bolum": "MANAGEMENT",
    "name": "MANAGEMENT"
  },
  {
    "kisaadi": "MIS",
    "bolum": "MANAGEMENT+INFORMATION+SYSTEMS",
    "name": "MANAGEMENT INFORMATION SYSTEMS"
  },
  {
    "kisaadi": "MATH",
    "bolum": "MATHEMATICS",
    "name": "MATHEMATICS"
  },
  {
    "kisaadi": "SCED",
    "bolum": "MATHEMATICS+AND+SCIENCE+EDUCATION",
    "name": "MATHEMATICS AND SCIENCE EDUCATION"
  },
  {
    "kisaadi": "ME",
    "bolum": "MECHANICAL+ENGINEERING",
    "name": "MECHANICAL ENGINEERING"
  },
  {
    "kisaadi": "BIO",
    "bolum": "MOLECULAR+BIOLOGY+%26+GENETICS",
    "name": "MOLECULAR BIOLOGY & GENETICS"
  },
  {
    "kisaadi": "PHIL",
    "bolum": "PHILOSOPHY",
    "name": "PHILOSOPHY"
  },
  {
    "kisaadi": "PE",
    "bolum": "PHYSICAL+EDUCATION",
    "name": "PHYSICAL EDUCATION"
  },
  {
    "kisaadi": "PHYS",
    "bolum": "PHYSICS",
    "name": "PHYSICS"
  },
  {
    "kisaadi": "POLS",
    "bolum": "POLITICAL+SCIENCE%26INTERNATIONAL+RELATIONS",
    "name": "POLITICAL SCIENCE&INTERNATIONAL RELATIONS"
  },
  {
    "kisaadi": "PSY",
    "bolum": "PSYCHOLOGY",
    "name": "PSYCHOLOGY"
  },
  {
    "kisaadi": "YADYOK",
    "bolum": "SCHOOL+OF+FOREIGN+LANGUAGES",
    "name": "SCHOOL OF FOREIGN LANGUAGES"
  },
  {
    "kisaadi": "SOC",
    "bolum": "SOCIOLOGY",
    "name": "SOCIOLOGY"
  },
  {
    "kisaadi": "SWE",
    "bolum": "SOFTWARE+ENGINEERING",
    "name": "SOFTWARE ENGINEERING"
  },
  {
    "kisaadi": "SWE",
    "bolum": "SOFTWARE+ENGINEERING+WITH+THESIS",
    "name": "SOFTWARE ENGINEERING WITH THESIS"
  },
  {
    "kisaadi": "TRM",
    "bolum": "SUSTAINABLE+TOURISM+MANAGEMENT",
    "name": "SUSTAINABLE TOURISM MANAGEMENT"
  },
  {
    "kisaadi": "SCO",
    "bolum": "SYSTEMS+%26+CONTROL+ENGINEERING",
    "name": "SYSTEMS & CONTROL ENGINEERING"
  },
  {
    "kisaadi": "TRM",
    "bolum": "TOURISM+MANAGEMENT",
    "name": "TOURISM MANAGEMENT"
  },
  {
    "kisaadi": "WTR",
    "bolum": "TRANSLATION",
    "name": "TRANSLATION"
  },
  {
    "kisaadi": "TR",
    "bolum": "TRANSLATION+AND+INTERPRETING+STUDIES",
    "name": "TRANSLATION AND INTERPRETING STUDIES"
  },
  {
    "kisaadi": "TK",
    "bolum": "TURKISH+COURSES+COORDINATOR",
    "name": "TURKISH COURSES COORDINATOR"
  },
  {
    "kisaadi": "TKL",
    "bolum": "TURKISH+LANGUAGE+%26+LITERATURE",
    "name": "TURKISH LANGUAGE & LITERATURE"
  },
  {
    "kisaadi": "PRSO",
    "bolum": "UNDERGRADUATE+PROGRAM+IN+PRESCHOOL+EDUCATION",
    "name": "UNDERGRADUATE PROGRAM IN PRESCHOOL EDUCATION"
  },
  {
    "kisaadi": "LL",
    "bolum": "WESTERN+LANGUAGES+%26+LITERATURES",
    "name": "WESTERN LANGUAGES & LITERATURES"
  }
];
