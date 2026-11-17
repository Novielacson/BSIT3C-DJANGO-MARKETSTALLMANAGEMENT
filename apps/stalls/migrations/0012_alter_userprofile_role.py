from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stalls', '0011_alter_userprofile_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(choices=[('superadmin', 'Superuser'), ('manager', 'Market Manager/Head'), ('staff', 'Staff / Collector')], default='staff', max_length=20),
        ),
    ]
