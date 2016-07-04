# Adding Signals to Django Projects

1) Add an AppConfig
   
in apps.py:

    from __future__ import unicode_literals

    from django.apps import AppConfig
    
    
    class EasyAccountConfig(AppConfig):
        name = 'easy_account'

        def ready(self):
            import signals

2) Replace app import in settings.py


    -     'easy_account'
    +     'easy_account.apps.EasyAccountConfig',

3) Add "signals.py" to your app

    import logging
    import uuid

    from django.db import models
    from django.db.models.signals import pre_save, pre_init
    from django.dispatch import receiver

    from .models import MoneyStore, BalanceCheck, Transaction, TransactionPlace, TransactionType

    logger = logging.getLogger(__name__)


    @receiver(pre_save, sender=MoneyStore)
    def initial_estimated_balance(sender, instance, **kwargs):
        print 'presave'
        # Make estimated balance = opening balance on model first save
        if instance.pk is None:
            instance.pk=uuid.uuid4()
            instance.estimatedbalance=instance.openingbalance

