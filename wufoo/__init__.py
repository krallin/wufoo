#!/usr/bin/env python
#coding:utf-8
# Make an HTML form out a Wufoo Form!

import os

import requests
import requests.auth
import bs4


WUFOO_API_FORMAT = "https://{domain}.wufoo.com/api/{version}"
WUFOO_FORM_FORMAT = "https://{domain}.wufoo.com/forms/{form_hash}/"
IGNORE_FIELDS = [u"EntryId", u"DateCreated", u"CreatedBy", u"LastUpdated", u"UpdatedBy"]


def join(*args):
    return os.path.join(*args).replace("\\", "/").rstrip("/")


class BaseField(object):
    #TODO: Support default / placeholder
    #TODO: Support Instructions
    #TODO: Support tabindex
    def __init__(self, field):
        self.field = field

    def get_class(self):
        klass = []
        if self.field[u"IsRequired"] == "1":
            klass.append("required")
        klass.extend(self.field[u"ClassNames"].split(" "))
        return klass

    def get_type(self):
        return self.field[u"Type"]

    def get_id(self):
        html_id = self.field.get(u"HTMLID")
        if html_id is None:
            html_id = self.field[u"ID"]
        return "-".join(("wufoo", html_id))

    def get_name(self):
        return self.field[u"ID"]

    def get_tag(self):
        return "input"

    def get_input(self, soup):
        input = soup.new_tag(self.get_tag())
        input["id"] = self.get_id()
        input["name"] = self.get_name()
        input["type"] = self.get_type()
        input["class"] = self.get_class()
        return input

    def get_label(self, soup):
        label = soup.new_tag("label")
        label["for"] = self.get_id()
        label["id"] = "-".join((self.get_id(), "label"))
        label["class"] = self.get_class()
        label.string = self.field[u"Title"]

        return label

    def extend_fieldset(self, soup, fieldset):
        input = self.get_input(soup)
        label = self.get_label(soup)
        fieldset.append(label)
        fieldset.append(input)

    def extend_form(self, soup, form):
        fieldset = soup.new_tag("fieldset")
        self.extend_fieldset(soup, fieldset)
        form.append(fieldset)


class InlineField(BaseField):
    def extend_fieldset(self, soup, fieldset):
        input = self.get_input(soup)
        label = self.get_label(soup)
        label.insert(0, input)
        fieldset.append(label)


class TextField(BaseField):
    pass

class EmailField(BaseField):
    def get_type(self):
        return "text"

    def get_class(self):
        klass = super(EmailField, self).get_class()
        klass.append("email")
        return klass


class URLField(BaseField):
    def get_type(self):
        return "text"

    def get_class(self):
        klass = super(URLField, self).get_class()
        klass.append("url")  #TODO: Check this works!
        return klass


class RadioField(InlineField):
    def get_input(self, soup):
        input = super(RadioField, self).get_input(soup)
        input["value"] = self.field[u"Label"]
        return input


class TextAreaField(BaseField):
    def get_type(self):
        return None

    def get_tag(self):
        return "textarea"


class FileField(BaseField):
    pass


class CheckboxField(InlineField):
    def get_input(self, soup):
        input = super(CheckboxField, self).get_input(soup)
        input["value"] = self.field[u"Label"]
        return input


class CompoundField(BaseField):
    SUBFIELD_ATTR = u"SubFields"

    def get_sub_field_type(self):
        raise NotImplementedError()

    def get_sub_field_title(self, sub_field):
        return sub_field["Label"]

    def get_legend(self, soup):
        legend = soup.new_tag("legend")
        legend.string = self.field["Title"]
        return legend

    def extend_form(self, soup, form):
        fieldset = soup.new_tag("fieldset")

        legend = self.get_legend(soup)
        if legend is not None:
            fieldset.append(legend)

        for i, sub_field in enumerate(self.field[self.SUBFIELD_ATTR]):
            f = dict(self.field)
            f.update(sub_field)
            f[u"Type"] = self.get_sub_field_type()
            f[u"Title"] = self.get_sub_field_title(sub_field)
            f[u"HTMLID"] = "-".join((self.get_id(), str(i)))
            Field(f).extend_fieldset(soup, fieldset)

        form.append(fieldset)


class ShortNameField(CompoundField):
    def get_legend(self, soup):
        return None

    def get_sub_field_title(self, sub_field):
        return " ".join([sub_field["Label"], self.field["Title"]])

    def get_sub_field_type(self):
        return "text"


class WufooCheckboxField(CompoundField):
    def get_sub_field_type(self):
        return "checkbox"


class WufooRadioField(CompoundField):
    SUBFIELD_ATTR = "Choices"

    def get_sub_field_type(self):
        return "radio"


FIELD_MAPPING = {
    "text": TextField,
    "wufoo-checkbox": WufooCheckboxField,  # Their checkbox model makes little sense
    "checkbox": CheckboxField,
    "wufoo-radio": WufooRadioField,
    "radio": RadioField,
    "email": EmailField,
    "shortname": ShortNameField,
    "url": URLField,
    "textarea": TextAreaField,
    "file": FileField,
}


TRANSFORM_TYPES = {
    "checkbox": "wufoo-checkbox",
    "radio": "wufoo-radio",
}

class Field(object):
    def __new__(cls, wufoo_field):
        type = wufoo_field[u"Type"]
        FieldClass = FIELD_MAPPING.get(type)
        assert FieldClass is not None, "Type %s is not supported" % type
        return FieldClass(wufoo_field)

class WufooClient(object):
    VERSION = "v3"
    FORMAT = "json"

    def __init__(self, domain, api_key):
        self.domain = domain
        self.api_url = WUFOO_API_FORMAT.format(domain=self.domain, version=self.VERSION)
        self.session = requests.session()
        self.session.auth = requests.auth.HTTPBasicAuth(api_key, "")

    def _url(self, *parts):
        path = [self.api_url]
        path.extend(parts)
        return ".".join((join(*path), self.FORMAT))

    def get_fields(self, form_hash):
        res = self.session.get(self._url("forms", form_hash, "fields"))
        print res.request.url
        return res.json()

    def make_form(self, form_id, form_hash, post_key):
        #TODO: Action and POST key https://scalr.wufoo.com/docs/api/v2/external-post-to-wufoo/
        fields = self.get_fields(form_hash)

        soup = bs4.BeautifulSoup()

        form = soup.new_tag("form")
        form["action"] = WUFOO_FORM_FORMAT.format(domain=self.domain, form_hash=form_hash)
        form["method"] = "post"
        form["id"] = form_id
        soup.append(form)

        for field in fields[u"Fields"]:
            if field[u"ID"] in IGNORE_FIELDS:
                continue

            for src, dst in TRANSFORM_TYPES.items():
                if field[u"Type"] == src:
                    field[u"Type"] = dst

            field = Field(field)
            field.extend_form(soup, form)

        post_key_input = soup.new_tag("input")
        post_key_input["type"] = "hidden"
        post_key_input["name"] = "idstamp"
        post_key_input["id"] = "wufoo-idstamp"
        post_key_input["value"] = post_key
        form.append(post_key_input)

        return soup


def make_form(client, form_hash, post_key):
    client = WufooClient(domain, api_key)
    return client.make_form(form_hash, post_key)
