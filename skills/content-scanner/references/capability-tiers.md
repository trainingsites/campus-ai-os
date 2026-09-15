# Capability tiers + internal-data buckets

Checked at runtime against ACTUAL session tools, not config. A bucket is `connected` only if its tool substring appears in the live tool list. No assumptions, no prompting to install.

## Search tier
| Tier | Tools | What changes |
|---|---|---|
| Premium | Firecrawl OR Apify | structured metadata, deep crawls, actor pulls |
| Baseline | WebSearch + WebFetch (always) | standard SERP + single-page reads |

## Internal-data buckets (1.5× multiplier when connected)
| Bucket | Tool substring | Multiplies topics matching |
|---|---|---|
| Revenue | sales_stats / list_orders | purchase patterns |
| Customer | list_campaigns / search_subscribers | email engagement |
| Community | list_feeds / list_comments | hot threads, unanswered Qs |
| Courses | course_analytics / course_progress | completion drop-offs, quiz fails |
| Content | get_posts / list_posts | already-covered guard |
| Calendar | list_events / list_calendars | timely/seasonal topics |

## business_model → source-weight defaults
| model | bucket-2 label | weight shifts | output defaults |
|---|---|---|---|
| courses | AI × Education | Community 35%, Course platform 25% | youtube_script, webinar, blog_post |
| coaching | AI × Coaching | Community 30%, Competitor 30% | workshop, zoom_session, newsletter |
| services | AI × [Industry] | Competitor 35%, General 25% | blog_post, linkedin_article, email_campaign |
| events | AI × Live Events | Community 35%, Calendar 20% | event desc, email_campaign, social_bundle |
| ecommerce | AI × Commerce | Competitor 30%, Reviews 25% | blog_post, social_bundle, email_campaign |
