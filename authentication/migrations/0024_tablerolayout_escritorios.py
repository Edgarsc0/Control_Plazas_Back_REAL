from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0023_modomantenimiento'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablerolayout',
            name='escritorios',
            field=models.JSONField(default=list),
        ),
    ]
