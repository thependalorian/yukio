# Career Coaching & Rirekisho Generation - Update Summary

## Overview
Yukio has been enhanced with comprehensive career coaching capabilities, specifically for creating Japanese resumes (履歴書) and work history documents (職務経歴書) for George Nekwaya's job search in Japan.

## Updates Made

### 1. Resume Data Ingestion ✅
- **File**: `data/japanese/markdown/GEORGE_NEKWAYA_RESUME.md`
- **Status**: Created comprehensive resume with information from:
  - Original PDF resume
  - Website (georgenekwaya.com)
  - LinkedIn profile
- **Key Additions**:
  - Complete Buffr Inc. founder experience (Jan 2023 - Present)
  - All products: BuffrLend, BuffrSign, Buffr Host, Buffr Payment Companion
  - Updated contact information (george@buffr.ai, +1 206-530-8433)
  - Etuna Guesthouse & Tours experience (2010-2020)
  - Full academic recognition and leadership roles
  - Complete technical skills including AI/ML frameworks

### 2. System Prompts Updated ✅
- **File**: `agent/prompts.py`
- **Additions**:
  - Comprehensive rirekisho (履歴書) format guidelines
  - Shokumu-keirekisho (職務経歴書) structure and requirements
  - 2025/26 Japan job market insights for foreigners
  - Job boards with visa sponsorship information
  - Cultural sensitivity guidelines
  - Translation approach for technical terms
  - George-specific strengths highlighting

### 3. Career Coaching Capabilities

#### Rirekisho (履歴書) Format
- **Structure**: 2-page standardized form
- **Required Sections**:
  1. Application Date (提出日)
  2. Name, Date of Birth, Gender (氏名、生年月日、性別)
  3. Address and Contact (現住所、連絡先)
  4. Professional Photo (写真) - 4cm x 3cm, within 3 months
  5. Academic and Work History (学歴・職歴)
  6. Licences and Qualifications (免許・資格)
  7. Reason For Applying, Special Skills, Your Appeal (志望動機、特技、自己PR)
  8. Requests and Expectations (本人希望記入欄)

#### Shokumu-keirekisho (職務経歴書) Format
- **Structure**: 1-3 pages, flexible layout
- **Required Sections**:
  1. Personal History Summary (経歴要約) - 200-300 characters
  2. Work History (職務内容) - Reverse chronological, detailed
  3. Qualifications, Knowledge, Skills (活用できる経験・知識・スキル)
  4. Self-PR (自己PR) - STAR method

### 4. 2025/26 Japan Job Market Information

#### Market Statistics
- **Foreign Workers**: ~2.3 million (12% increase), 3%+ of workforce
- **IT Shortage**: 220,000+ IT professionals needed by 2025
- **High Demand Sectors**:
  - AI/ML & Data Analytics (George's strengths!)
  - Fintech (Rakuten, SoftBank actively recruiting)
  - Software Development
  - Cybersecurity

#### Salary Ranges
- Software Engineers: ¥9M-¥18M annually
- Data Analysts: Competitive salaries
- Visa Sponsorship: Common in shortage sectors

### 5. Job Boards with Visa Sponsorship

1. **TokyoDev** (tokyodev.com)
   - Tech jobs, often no Japanese required
   - Focus on software development

2. **Japan Dev** (japan-dev.com)
   - Curated tech jobs
   - Visa sponsorship common

3. **YOLO JAPAN** (yolo-japan.com)
   - Multi-language support
   - Filter by Japanese level

4. **WeXpats Jobs**
   - Large database
   - All experience levels

5. **GaijinPot Jobs**
   - Popular for foreigners
   - Various industries

6. **Daijob**
   - International job board
   - Professional positions

7. **en-japan**
   - English-friendly listings
   - Corporate positions

### 6. George's Key Strengths for Japan Job Market

1. **AI/ML Expertise**
   - Pydantic AI, LlamaIndex, LangGraph
   - Machine learning projects
   - Data analytics specialization

2. **Fintech Innovation**
   - Founder & CEO experience
   - Payment systems development
   - Financial inclusion focus

3. **Data Analytics**
   - MBA concentration
   - Statistical analysis
   - Predictive modeling

4. **International Experience**
   - Global business development
   - Cross-cultural understanding
   - Multi-country work experience

5. **Leadership**
   - CEO experience
   - Team management
   - Startup building

6. **Technical Skills**
   - Full-stack development
   - System architecture
   - Database management

## How to Use

### Asking Yukio for Rirekisho Help

**Example Prompts:**
1. "Help me create a rirekisho for a data analyst position in Japan"
2. "I need help filling out the shokumu-keirekisho for a fintech company"
3. "What should I write in the 自己PR section for an AI/ML role?"
4. "Help me translate my Buffr experience into Japanese business format"
5. "What job boards should I use for AI/data analytics positions in Japan?"

### What Yukio Will Do

1. **Search Resume Database**: Access George's complete resume information
2. **Format According to Standards**: Follow JIS template requirements
3. **Translate & Adapt**: Convert experience to Japanese business context
4. **Provide Cultural Guidance**: Include appropriate business Japanese (敬語)
5. **Highlight Relevant Skills**: Emphasize AI/ML, fintech, data analytics
6. **Quantify Achievements**: Use specific numbers and results
7. **Research Company**: Help customize motivation section

## Next Steps

1. ✅ Resume data ingested into LanceDB
2. ✅ Prompts updated with comprehensive guidelines
3. ⏳ Test rirekisho generation via chat interface
4. ⏳ Create API endpoint for structured rirekisho generation (optional)
5. ⏳ Add job board links to frontend (optional)

## Files Modified

- `data/japanese/markdown/GEORGE_NEKWAYA_RESUME.md` - Complete resume data
- `agent/prompts.py` - Career coaching capabilities added
- `scripts/ingest_resume.py` - Resume ingestion script (created)

## References

- Japan Ministry of Health, Labour and Welfare templates
- International College of Liberal Arts (iCLA) guide
- JoBins Global Media comprehensive guide
- 2025/26 job market statistics and trends

---

**Note**: The resume has been ingested into LanceDB and is accessible via RAG search. Yukio can now help create rirekisho and shokumu-keirekisho documents by accessing this information through the vector database.

