from pywikibot import family

class Family(family.Family):  # noqa: D101

    name = 'kateb'
    langs = {
        'fa': 'user:pass@URL',  # uesr:pass of web server authentication
    }

    def scriptpath(self, code):
        return {
            'fa': '/w',
        }[code]

    def protocol(self, code):
        return {
            'fa': 'https',
        }[code]
