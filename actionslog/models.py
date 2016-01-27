
from __future__ import unicode_literals

import json

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import QuerySet, Q
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.translation import ugettext_lazy as _

from jsonfield import JSONField


class LogActionManager(models.Manager):

    def create_log_action(self, **kwargs):
        """
        Helper method to create a new log entry. This method automatically populates some fields when no explicit value
        is given.
        :param instance: The model instance to log a change for.
        :type instance: Model
        :param kwargs: Field overrides for the :py:class:`LogEntry` object.
        :return: The new log entry or `None` if there were no changes.
        :rtype: LogEntry
        """
        instance = kwargs.get('instance', None)
        pk = self._get_pk_value(instance)

        if instance is not None and changes is not None:
            kwargs.setdefault('content_type', ContentType.objects.get_for_model(instance))
            kwargs.setdefault('object_pk', pk)
            kwargs.setdefault('object_repr', smart_text(instance))

            if isinstance(pk, integer_types):
                kwargs.setdefault('object_id', pk)

            get_object_extra_info = getattr(instance, 'get_object_extra_info', None)
            if callable(get_object_extra_info):
                kwargs.setdefault('object_extra_info', get_object_extra_info())

            # Delete log entries with the same pk as a newly created model. This should only be necessary when an pk is
            # used twice.
            if kwargs.get('action', None) is LogEntry.CREATE:
                if kwargs.get('object_id', None) is not None and self.filter(content_type=kwargs.get('content_type'), object_id=kwargs.get('object_id')).exists():
                    self.filter(content_type=kwargs.get('content_type'), object_id=kwargs.get('object_id')).delete()
                else:
                    self.filter(content_type=kwargs.get('content_type'), object_pk=kwargs.get('object_pk', '')).delete()

        return self.create(**kwargs)
        return None

    def get_for_model(self, model):
        """
        Get log entries for all objects of a specified type.
        :param model: The model to get log entries for.
        :type model: class
        :return: QuerySet of log entries for the given model.
        :rtype: QuerySet
        """
        # Return empty queryset if the given object is not valid.
        if not issubclass(model, models.Model):
            return self.none()

        ct = ContentType.objects.get_for_model(model)

        return self.filter(content_type=ct)

    def get_for_objects(self, queryset):
        """
        Get log entries for the objects in the specified queryset.
        :param queryset: The queryset to get the log entries for.
        :type queryset: QuerySet
        :return: The LogEntry objects for the objects in the given queryset.
        :rtype: QuerySet
        """
        if not isinstance(queryset, QuerySet) or queryset.count() == 0:
            return self.none()

        content_type = ContentType.objects.get_for_model(queryset.model)
        primary_keys = queryset.values_list(queryset.model._meta.pk.name, flat=True)

        if isinstance(primary_keys[0], integer_types):
            return self.filter(content_type=content_type).filter(Q(object_id__in=primary_keys)).distinct()
        else:
            return self.filter(content_type=content_type).filter(Q(object_pk__in=primary_keys)).distinct()

    def _get_pk_value(self, instance):
        """
        Get the primary key field value for a model instance.
        :param instance: The model instance to get the primary key for.
        :type instance: Model
        :return: The primary key value of the given model instance.
        """
        pk_field = instance._meta.pk.name
        pk = getattr(instance, pk_field, None)

        # Check to make sure that we got an pk not a model object.
        if isinstance(pk, models.Model):
            pk = self._get_pk_value(pk)
        return pk


@python_2_unicode_compatible
class LogAction(models.Model):

    CREATE = 10
    VIEW = 15
    CHANGE = 20
    DELETE = 30

    ACTION_CHOICES = (
        (CREATE, _("create")),
        (VIEW, _("view")),
        (CHANGE, _("change")),
        (DELETE, _("delete")),
    )

    content_type = models.ForeignKey('contenttypes.ContentType', related_name='+',
        verbose_name=_("content type"), blank=True, null=True, on_delete=models.CASCADE)
    object_id = models.BigIntegerField(verbose_name=_("object id"),
        bank=True, null=True, db_index=True,)
    object_pk = models.CharField(verbose_name=_("object pk"), max_length=255,
        blank=True, null=True, db_index=True)

    object_repr = models.TextField(verbose_name=_("object representation"), blank=True, null=True)
    object_extra_info = JSONField(verbose_name=_("object information"), blank=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user"),
        blank=True, null=True, on_delete=models.SET_NULL, related_name='actionlogs')
    action = models.PositiveSmallIntegerField(verbose_name=_("action"),
        choices=ACTION_CHOICES, bank=True, null=True)

    action_info = JSONField(verbose_name=_("action information"), blank=True, null=True, )
    changes = models.TextField(blank=True, verbose_name=_("change message"))

    remote_ip = models.GenericIPAddressField(verbose_name=_("remote IP"), blank=True, null=True)
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)

    objects = LogActionManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("log action")
        verbose_name_plural = _("log actions")

    def __str__(self):
        return _("Logged {repr:s}").format(repr=self.object_repr)

    property
    def changes_dict(self):
        """
        :return: The changes recorded in this log entry as a dictionary object.
        """
        try:
            return json.loads(self.changes)
        except ValueError:
            return {}

    @property
    def changes_str(self, colon=': ', arrow=smart_text(' \u2192 '), separator='; '):
        """
        Return the changes recorded in this log entry as a string. The formatting of the string can be customized by
        setting alternate values for colon, arrow and separator. If the formatting is still not satisfying, please use
        :py:func:`LogEntry.changes_dict` and format the string yourself.
        :param colon: The string to place between the field name and the values.
        :param arrow: The string to place between each old and new value.
        :param separator: The string to place between each field.
        :return: A readable string of the changes in this log entry.
        """
        substrings = []

        for field, values in iteritems(self.changes_dict):
            substring = smart_text('{field_name:s}{colon:s}{old:s}{arrow:s}{new:s}').format(
                field_name=field,
                colon=colon,
                old=values[0],
                arrow=arrow,
                new=values[1],
            )
            substrings.append(substring)

        return separator.join(substrings)
