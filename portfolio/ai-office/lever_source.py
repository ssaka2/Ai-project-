"""Read-only adapter for Lever's documented public postings API."""
import html
import re
from urllib.parse import urlsplit


def text(value):
    if not isinstance(value, str):
        raise ValueError('Invalid posting text')
    return re.sub(r'<[^>]*>', ' ', html.unescape(value))


def fetch(site, read_json):
    jobs, seen = [], set()
    # A partial or repeating feed must never become a successful baseline.
    for page in range(10):
        body = read_json(f'https://api.lever.co/v0/postings/{site}?mode=json&skip={page*100}&limit=100')
        if not isinstance(body, list) or len(body)>100:
            raise ValueError('Invalid Lever page')
        for item in body:
            if not isinstance(item, dict):
                raise ValueError('Invalid Lever posting')
            identifier = item.get('id')
            if not isinstance(identifier, str) or not identifier.strip() or len(identifier)>200 or identifier in seen:
                raise ValueError('Invalid or repeated Lever posting ID')
            seen.add(identifier)
            title = text(item.get('text'))
            categories = item.get('categories')
            if not isinstance(categories, dict):
                raise ValueError('Invalid Lever categories')
            location = text(categories.get('location', ''))
            locations = categories.get('allLocations', [])
            if not isinstance(locations, list) or any(not isinstance(x,str) for x in locations):
                raise ValueError('Invalid Lever locations')
            location = ' / '.join(dict.fromkeys([location, *locations]))
            url = item.get('hostedUrl')
            if not isinstance(url, str):
                raise ValueError('Missing Lever URL')
            parsed = urlsplit(url)
            if parsed.scheme!='https' or parsed.hostname!='jobs.lever.co' or parsed.username or parsed.password or parsed.port not in (None,443):
                raise ValueError('Invalid Lever hosted URL')
            description = [text(item.get('descriptionPlain'))]
            lists = item.get('lists', [])
            if not isinstance(lists,list):
                raise ValueError('Invalid Lever requirements')
            for entry in lists:
                if not isinstance(entry,dict):
                    raise ValueError('Invalid Lever requirement')
                description.extend([text(entry.get('text','')),text(entry.get('content',''))])
            description.extend([text(item.get('additionalPlain','')),text(item.get('salaryDescriptionPlain',''))])
            for key,value in [('Employment type',categories.get('commitment','')),('Workplace',item.get('workplaceType',''))]:
                description.append(key+': '+text(value))
            country = item.get('country')
            if country is not None:
                if not isinstance(country,str):
                    raise ValueError('Invalid Lever country')
                description.append('Country: '+country)
            # Unknown remote eligibility and publication dates remain unknown.
            jobs.append(dict(id=identifier,title=title[:500],url=url[:2000],location=location[:1000],description='\n'.join(description)[:50000]))
        if len(body)<100:
            return jobs
    raise ValueError('Lever page limit reached; no partial baseline saved')
