---
id: favorchurch/speak-like-favor
name: Speak Like Favor
contributor: favorchurch
origin: false
genericSkillRef: humanize-prose
status: named
level: 2★
description: Draft, edit, or QA Favor Church Manila communication so it feels warm,
  clear, and authentic.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Speak Like Favor
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/speak-like-favor/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:04Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/speak-like-favor
---

# Speak Like Favor

Use this skill to draft, edit, or QA Favor Church Manila communication so it feels warm, clear, authentic, and easy for people to act on.

## Prerequisites

**None.** This skill is pure writing and QA guidance, so it works in any AI assistant with no external connections, MCP servers, or CLI tools. If a task asks you to *send* or *publish* the copy (e.g. email a draft), that delivery step belongs to another skill or tool, not this one.

## Core Voice

Write like a friendly peer and helpful thought partner. Keep copy warm, human, and concise.

- Sound casual, clear, genuine, and encouraging.
- Avoid Christianese, stiff church jargon, preachy phrasing, and overly formal wording.
- Keep invitations confident and direct. Write `Join us!`, not `Please join us!`.
- Prefer simple phrasing over long sentences that do not connect.
- For visitors and public copy, make the message friendly, non-threatening, and easy to understand.
- For leaders and volunteers, sound clear, motivating, understanding, and team-oriented. Prefer `we` when it feels natural.
- For correction or sensitive copy, be truthful, patient, non-judgmental, and kind.

## Output Format

Default to scannable email-style formatting unless the user asks for another format.

- Start warm: `Hey, [Name]!`
- Use short paragraphs.
- Use bolding for key labels, dates, deadlines, venues, and action items.
- Use bullets for lists, not hyphen lists, unless a numbered sequence is clearer.
- End emails with:

```text
Much love,
XXX Team
```

Replace `XXX Team` with the relevant team, for example `Favor Conference Team`.

## Mechanical Rules

Apply these rules strictly when drafting or editing.

- Use English only.
- Never use the word `fam`.
- Never use an em dash. Use a comma, colon, semicolon, period, or parentheses instead.
- Do not start sentences with `And`.
- Use the Oxford comma: `read, think, and pray`.
- Use numerals for web and digital copy.
- Use `₱` for currency, for example `₱100`. Use `PHP` only when the peso sign is unavailable.
- Remove `https://`, `http://`, and `www` from visible links unless a platform specifically requires the full URL.
- Use lowercase links unless case-sensitive, for example `favor.church/mnl`.
- If a long public link will be used long-term, suggest a `favor.church` shortlink. For temporary internal links, `tinyurl.com` or `bit.ly` is acceptable.

## Dates and Times

Use Favor date and time formatting.

- Use `Jan 1`, never `Jan 1st` or `1st of Jan`.
- Use the full month when space allows.
- Use `AM` and `PM` with no space: `7AM`, `7:15PM`.
- Do not write `7:00PM`; write `7PM`.
- For invitations, use this order:

```text
Saturday, March 8, 10AM
Favor Studio, Shangri-La Plaza
```

## Names, Ministry Terms, and Capitalization

Apply Favor-specific terms carefully.

- Use `Church` for the universal body of believers.
- Use `church` for a service, building, or organization.
- Use `Connect Group` on first mention. `Connect` is acceptable after the first mention.
- Capitalize official ministries and communities: `Favor Kids`, `Favor Girl`, `Favor Men`, `Favor Youth`, `Favor Movement`, `Favor Adults`, `Favor Pro`, `Favor Seasoned`, `Favor Business`, and `Favor College`.
- Use `Favor Girl`, not `Favor Girls`, unless quoting existing approved copy that intentionally uses another form.
- Do not capitalize common group names unless directly addressing them: `Favor parents and guardians`, `Favor leaders`, `Connect Group leader`.
- When addressing groups directly, capitalization may be appropriate, for example `Hey, Connect Leaders!`.
- Use `Ps` for Pastor, with no period. When unsure, use the full title, for example `Pastors James and Kate Aiton`.
- Use `PS.` only for postscript.

## God, Jesus, Bible, and Theological References

Keep language clear and theologically careful without sounding heavy.

- Use lowercase pronouns for God, Jesus, and the Holy Spirit: `he`, `him`, `his`, `you`.
- If referring to God, Jesus, or the Holy Spirit in captions, use the name first, then lowercase pronouns after.
- Check basic theological accuracy. Do not refer to Jesus as the Father, or say the Father died for our sins.
- Use `gospel` for the good news of Jesus.
- Use `Gospel` when referring to a book of the Bible, for example `Gospel of John`.
- Use `Word` when referring to Jesus as the Word made flesh.
- Use `word` for a message, teaching, or spoken word from God.
- Bible references do not need parentheses. Examples: `Matt 10:28 NIV`, `Matthew 10:28 NIV`.

## Venues

Use full venue names.

- `Favor Studio, Shangri-La Plaza`
- `Favor Care, Shangri-La Plaza`
- `Favor Office, Shangri-La Plaza`
- `ICS Church, Greenfield District`
- `Metrotent Convention Center`
- `PhilSports Arena, Pasig`
- `Podium Hall, 6F at The Podium, Ortigas`
- `The Study, 4F at The Podium, Ortigas`
- `Valle Verde 5 Clubhouse, Pasig`
- `Valle Verde Country Club, Pasig`
- `Ynares Sports Arena, Pasig`

## Drafting Workflow

When creating or editing copy:

1. Identify the audience, channel, and action needed.
2. Apply Favor voice first, then shorten and clarify.
3. Check formatting, dates, times, links, venues, capitalization, currency, and theological references.
4. For emails, add the required `Much love,` team closing unless the user asks otherwise.
5. If key details are missing but the task can still be completed, use clear placeholders like `[Date]`, `[Time]`, `[Venue]`, and `[Link]` rather than blocking.
6. Before any tool calls for a multi-step task, send a short user-visible update that acknowledges the request and states the first step.

## QA Checklist

Before finalizing, scan for:

- No em dashes.
- No sentence starts with `And`.
- No use of `fam`.
- No unnecessary `please` in invitations.
- No Christianese or insider-only phrasing.
- Dates and times follow Favor format.
- Links have no `https://`, `http://`, or `www` in visible text.
- Venue names are complete.
- Official group names are capitalized correctly.
- God/Jesus/Holy Spirit pronouns are lowercase.
- Email closing uses `Much love,` and the right team name.

For fuller QA standards, consult `references/qa-guidelines.md` when the user asks for a detailed QA review, social media QA, visual/video requirements, or a more comprehensive source of Favor standards.
