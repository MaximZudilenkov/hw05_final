import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )
        cls.second_group = Group.objects.create(
            title='Новая группа',
            slug='group-new-slug',
            description='Описание новой группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )

        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
            post=cls.post
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif')
        form_data = {
            'text': 'Новый созданный текст',
            'group': self.group.pk,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        test_post = Post.objects.first()
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(test_post.text, form_data['text'])
        self.assertEqual(test_post.group.title, self.group.title)
        self.assertEqual(test_post.image.size, uploaded.size)

    def test_edit_post(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'Измененный пост',
            'group': self.second_group.pk, }
        self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
        )
        updated_post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(updated_post.text, form_data['text'])
        self.assertEqual(updated_post.group, self.second_group)

    def test_create_comment_for_logged_and_unlogged_users(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }

        response_for_unlogged_users = self.guest_client.get(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            follow=True
        )

        response_for_logged_users = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response_for_unlogged_users,
            f'/auth/login/?next=/posts/{self.post.pk}/comment/'
        )

        self.assertRedirects(
            response_for_logged_users,
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
