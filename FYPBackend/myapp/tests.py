# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APITestCase
# from .models import CustomUser, Property, House, Features, PropertyImage, PropertyType, UserRole
# from django.core.files.uploadedfile import SimpleUploadedFile
# import tempfile
# from PIL import Image

# class PropertyAPITests(APITestCase):
#     def setUp(self):
#         # Create users
#         self.seller_user = CustomUser.objects.create_user(
#             email='seller@example.com',
#             username='seller',
#             full_name='Test Seller',
#             role=UserRole.SELLER,
#             password='password123'
#         )
#         self.another_seller_user = CustomUser.objects.create_user(
#             email='seller2@example.com',
#             username='seller2',
#             full_name='Another Seller',
#             role=UserRole.SELLER,
#             password='password123'
#         )
#         self.buyer_user = CustomUser.objects.create_user(
#             email='buyer@example.com',
#             username='buyer',
#             full_name='Test Buyer',
#             role=UserRole.BUYER,
#             password='password123'
#         )
        
#         # Create some features
#         self.feature1 = Features.objects.create(name="Swimming Pool")
#         self.feature2 = Features.objects.create(name="Garden")

#         # Create a property for the main seller
#         self.property = Property.objects.create(
#             user=self.seller_user,
#             title="Seller's Original House",
#             property_type=PropertyType.HOUSE,
#             location="http://example.com/location1",
#             sale_type="sale",
#             sale_price="600000.00"
#         )
        
#         # URLs
#         self.properties_url = reverse('property-list')
#         self.property_detail_url = reverse('property-detail', kwargs={'pk': self.property.pk})

#     def test_unauthenticated_user_cannot_access_properties(self):
#         """
#         Ensure unauthenticated users get a 401 Unauthorized response.
#         """
#         response = self.client.get(self.properties_url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_buyer_is_forbidden_from_property_endpoints(self):
#         """
#         Ensure a user with the 'buyer' role gets a 403 Forbidden response.
#         """
#         self.client.force_authenticate(user=self.buyer_user)
#         # Test list view
#         response_get = self.client.get(self.properties_url)
#         self.assertEqual(response_get.status_code, status.HTTP_403_FORBIDDEN)
#         # Test creation
#         response_post = self.client.post(self.properties_url, {}, format='json')
#         self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)

#     def test_seller_can_create_property_with_nested_data(self):
#         """
#         Ensure a seller can create a property with nested data (e.g., a House).
#         """
#         self.client.force_authenticate(user=self.seller_user)
        
#         house_data = {
#             "bedrooms": 4,
#             "bathrooms": 3,
#             "builtup_area": 2200,
#             "year_built": 2021,
#             "plot_size": 450,
#             "floors": 2,
#             "features": [self.feature1.id, self.feature2.id],
#             "description": "A beautiful new family home."
#         }
        
#         property_data = {
#             "property_type": "house",
#             "title": "My Newest House",
#             "location": "http://example.com/location_new",
#             "sale_type": "sale",
#             "sale_price": "750000.00",
#             "house": house_data
#         }
        
#         response = self.client.post(self.properties_url, property_data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(Property.objects.count(), 2) # One from setUp, one from this test
#         self.assertTrue(Property.objects.filter(title="My Newest House").exists())
#         new_property = Property.objects.get(title="My Newest House")
#         self.assertTrue(hasattr(new_property, 'house'))
#         self.assertEqual(new_property.house.bedrooms, 4)
#         self.assertEqual(new_property.house.features.count(), 2)

#     def test_seller_can_list_only_their_own_properties(self):
#         """
#         Ensure the property list view only returns properties owned by the authenticated seller.
#         """
#         # Create a property for the other seller
#         Property.objects.create(user=self.another_seller_user, title="Another Seller's House", property_type=PropertyType.HOUSE, location="http://example.com/location2", sale_price=1)
        
#         self.client.force_authenticate(user=self.seller_user)
#         response = self.client.get(self.properties_url)
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         # The main seller only has one property from setUp
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]['title'], "Seller's Original House")

#     def test_seller_can_update_own_property(self):
#         """
#         Ensure a seller can update their own property.
#         """
#         self.client.force_authenticate(user=self.seller_user)
#         update_data = {'title': 'Updated Property Title'}
#         response = self.client.patch(self.property_detail_url, update_data, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.property.refresh_from_db()
#         self.assertEqual(self.property.title, 'Updated Property Title')

#     def test_seller_cannot_access_another_sellers_property(self):
#         """
#         Ensure a seller gets a 404 when trying to access another seller's property.
#         """
#         other_property = Property.objects.create(user=self.another_seller_user, title="Other Prop", property_type=PropertyType.HOUSE, location="http://example.com/location3", sale_price=1)
#         other_detail_url = reverse('property-detail', kwargs={'pk': other_property.pk})

#         self.client.force_authenticate(user=self.seller_user)
        
#         response_get = self.client.get(other_detail_url)
#         self.assertEqual(response_get.status_code, status.HTTP_404_NOT_FOUND)
        
#         response_put = self.client.put(other_detail_url, {}, format='json')
#         self.assertEqual(response_put.status_code, status.HTTP_404_NOT_FOUND)

#     def test_seller_can_delete_own_property(self):
#         """
#         Ensure a seller can delete their own property.
#         """
#         self.client.force_authenticate(user=self.seller_user)
#         response = self.client.delete(self.property_detail_url)
#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
#         self.assertFalse(Property.objects.filter(pk=self.property.pk).exists())
        
#     def test_seller_can_upload_image_to_own_property(self):
#         """
#         Ensure a seller can upload an image to their property.
#         """
#         self.client.force_authenticate(user=self.seller_user)
        
#         # Create a temporary image file for upload
#         with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
#             img = Image.new('RGB', (100, 100), color='red')
#             img.save(tmp_file, format='JPEG')
#             tmp_file.seek(0)
            
#             upload_url = reverse('property-upload-image', kwargs={'pk': self.property.pk})
#             data = {'image': tmp_file}
            
#             response = self.client.post(upload_url, data, format='multipart')

#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(PropertyImage.objects.count(), 1)
#         self.assertEqual(self.property.images.count(), 1)


# class PropertyBrowsingAPITests(APITestCase):
#     def setUp(self):
#         # Create a seller and a buyer user
#         self.seller_user = CustomUser.objects.create_user(
#             email='browser_seller@example.com', username='browser_seller', full_name='Browser Seller', role=UserRole.SELLER, password='password123'
#         )
#         self.buyer_user = CustomUser.objects.create_user(
#             email='browser_buyer@example.com', username='browser_buyer', full_name='Browser Buyer', role=UserRole.BUYER, password='password123'
#         )

#         # Create properties with different statuses
#         # Active and visible
#         Property.objects.create(
#             user=self.seller_user, title='Active House', property_type=PropertyType.HOUSE, location='City Center',
#             sale_price=1000, status='active', is_available=True, is_verified=True
#         )
#         # Inactive
#         Property.objects.create(
#             user=self.seller_user, title='Inactive House', property_type=PropertyType.HOUSE, location='Suburb',
#             sale_price=2000, status='inactive', is_available=True, is_verified=True
#         )
#         # Not available
#         Property.objects.create(
#             user=self.seller_user, title='Sold House', property_type=PropertyType.HOUSE, location='Countryside',
#             sale_price=3000, status='active', is_available=False, is_verified=True
#         )
#         # Not verified
#         Property.objects.create(
#             user=self.seller_user, title='Unverified Apartment', property_type=PropertyType.APARTMENT, location='City Center',
#             sale_price=4000, status='active', is_available=True, is_verified=False
#         )
#         # Another active one for ordering tests
#         Property.objects.create(
#             user=self.seller_user, title='Pricey Active Apartment', property_type=PropertyType.APARTMENT, location='Downtown',
#             sale_price=5000, status='active', is_available=True, is_verified=True
#         )

#         self.browse_url = reverse('property-browse')

#     def test_authenticated_user_can_browse_properties(self):
#         """
#         Ensure any authenticated user (e.g., a buyer) can access the browse endpoint.
#         """
#         self.client.force_authenticate(user=self.buyer_user)
#         response = self.client.get(self.browse_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_unauthenticated_user_cannot_browse_properties(self):
#         """
#         Ensure unauthenticated users get a 401 response.
#         """
#         response = self.client.get(self.browse_url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_browse_returns_only_active_available_verified_properties(self):
#         """
#         Ensure the browse endpoint filters properties correctly.
#         """
#         self.client.force_authenticate(user=self.buyer_user)
#         response = self.client.get(self.browse_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         # Only 'Active House' and 'Pricey Active Apartment' should be listed
#         self.assertEqual(len(response.data), 2)
#         titles = {item['title'] for item in response.data}
#         self.assertIn('Active House', titles)
#         self.assertIn('Pricey Active Apartment', titles)

#     def test_property_search(self):
#         """
#         Test the search functionality of the browse endpoint.
#         """
#         self.client.force_authenticate(user=self.buyer_user)
#         # Search by title
#         response = self.client.get(self.browse_url + '?search=Active House')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]['title'], 'Active House')

#         # Search by location
#         response = self.client.get(self.browse_url + '?search=Downtown')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]['title'], 'Pricey Active Apartment')

#         # Search by property type
#         response = self.client.get(self.browse_url + '?search=apartment')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)

#     def test_property_ordering(self):
#         """
#         Test the ordering functionality of the browse endpoint.
#         """
#         self.client.force_authenticate(user=self.buyer_user)
#         # Order by sale_price ascending
#         response = self.client.get(self.browse_url + '?ordering=sale_price')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 2)
#         self.assertEqual(response.data[0]['title'], 'Active House') # Price 1000
#         self.assertEqual(response.data[1]['title'], 'Pricey Active Apartment') # Price 5000
        
#         # Order by sale_price descending
#         response = self.client.get(self.browse_url + '?ordering=-sale_price')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 2)
#                 self.assertEqual(response.data[0]['title'], 'Pricey Active Apartment')
#                 self.assertEqual(response.data[1]['title'], 'Active House')
        
#             def test_authenticated_user_can_retrieve_detail_view(self):
#                 """
#                 Ensure an authenticated user can retrieve the detail view for an active property.
#                 """
#                 active_property = Property.objects.get(title='Active House')
#                 detail_url = reverse('property-detail-browse', kwargs={'pk': active_property.pk})
                
#                 self.client.force_authenticate(user=self.buyer_user)
#                 response = self.client.get(detail_url)
                
#                 self.assertEqual(response.status_code, status.HTTP_200_OK)
#                 self.assertEqual(response.data['title'], 'Active House')
        
#             def test_user_cannot_retrieve_inactive_property_detail(self):
#                 """
#                 Ensure a 404 is returned when trying to access an inactive property.
#                 """
#                 inactive_property = Property.objects.get(title='Inactive House')
#                 detail_url = reverse('property-detail-browse', kwargs={'pk': inactive_property.pk})
                
#                 self.client.force_authenticate(user=self.buyer_user)
#                 response = self.client.get(detail_url)
                
#                 self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
#             def test_user_cannot_retrieve_unavailable_property_detail(self):
#                 """
#                 Ensure a 404 is returned when trying to access a property that is not available.
#                 """
#                 unavailable_property = Property.objects.get(title='Sold House')
#                 detail_url = reverse('property-detail-browse', kwargs={'pk': unavailable_property.pk})
                
#                 self.client.force_authenticate(user=self.buyer_user)
#                 response = self.client.get(detail_url)
                
#                 self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
#             def test_user_cannot_retrieve_unverified_property_detail(self):
#                 """
#                 Ensure a 404 is returned when trying to access an unverified property.
#                 """
#                 unverified_property = Property.objects.get(title='Unverified Apartment')
#                 detail_url = reverse('property-detail-browse', kwargs={'pk': unverified_property.pk})
                
#                 self.client.force_authenticate(user=self.buyer_user)
#                 response = self.client.get(detail_url)
                
#                 self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        